"""v1.0: 第2工程の根拠・集計・引き渡しをオフライン検査する。

標準ライブラリのみ。外部取得や投稿、ファイル修正は行わない。
入力値の真偽や人気を自動認定せず、原本との内容照合は人が行う。
"""
import argparse
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from statistics import median

PRIMARY = {"primary_sold_search", "primary_sold_detail"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("時刻にはUTCオフセットが必要です")
    return result


def positive(value):
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() and amount > 0 else None
    except (InvalidOperation, ValueError):
        return None


def stats(rows):
    """価格不明の成約も需要には残す。件数は出品ID数であり販売枚数ではない。"""
    price_rows = [r for r in rows if r["price"]["basis"] == "sold_display"
                  and positive(r["price"].get("amount")) is not None]
    prices = [Decimal(str(r["price"]["amount"])) for r in price_rows]
    seller_counts = Counter(r["seller"] for r in rows)
    return {
        "records": len(rows), "sellers": len(seller_counts),
        "days": len({r["sold_date"] for r in rows}),
        "known_price_records": len(prices),
        "median_item_price": str(median(prices)) if prices else None,
        "min_item_price": str(min(prices)) if prices else None,
        "max_item_price": str(max(prices)) if prices else None,
        "seller_counts": dict(sorted(seller_counts.items())),
        "item_ids": [r["item_id"] for r in rows],
    }


def aggregate(record, rows, sources):
    criteria = record["criteria"]
    start = date.fromisoformat(record["window"]["start"])
    end = date.fromisoformat(record["window"]["end"])
    recent_start = max(start, end - timedelta(days=6))
    candidates = {c["id"]: c for c in record["candidates"]}
    buckets = {key: [] for key in candidates}
    counts = {key: Counter() for key in candidates}
    audits, seen, errors = [], set(), []
    for index, row in enumerate(rows):
        cid = row.get("candidate_id")
        reasons = []
        status = "included"
        if cid not in candidates:
            errors.append(f"observations[{index}]: unknown candidate_id")
            continue
        counts[cid]["retrieved"] += 1
        source = sources.get(row.get("source_id"), {})
        if not source:
            errors.append(f"observations[{index}]: source_id missing")
        if source.get("kind") not in PRIMARY or row.get("sold_confirmed") is not True:
            reasons.append("primary_sold_evidence_missing")
            status = "held"
        for field in ("item_id", "seller", "url", "identity_basis", "condition_basis", "unit_basis"):
            if not row.get(field):
                reasons.append(field + "_missing")
                status = "held"
        key = (source.get("platform"), row.get("item_id"))
        if key in seen:
            reasons.append("duplicate_item_id")
            status = "excluded"
        seen.add(key)
        for field in ("product_key", "language", "condition", "unit"):
            expected = candidates[cid][field]
            actual = row.get(field)
            if actual != expected:
                reasons.append(field + "_mismatch_or_unknown")
                if status != "excluded":
                    status = "held" if actual in (None, "unknown") else "excluded"
        if row.get("graded") is not False:
            reasons.append("graded_or_unknown")
            status = "excluded" if row.get("graded") is True else "held"
        if row.get("seller_country") != criteria["country"]:
            reasons.append("seller_country_mismatch_or_unknown")
            status = "excluded"
        try:
            sold_date = date.fromisoformat(row["sold_date"])
            if not start <= sold_date <= end:
                reasons.append("outside_date_window")
                status = "excluded"
        except (ValueError, KeyError, TypeError):
            reasons.append("sold_date_unknown")
            status = "held" if status != "excluded" else status
        price = row.get("price", {})
        if price.get("currency") != criteria["currency"]:
            reasons.append("currency_mismatch_or_unknown")
            status = "held" if status != "excluded" else status
        if price.get("basis") not in ("sold_display", "offer_unknown", "unknown"):
            errors.append(f"observations[{index}]: unsupported price basis")
        if price.get("basis") in ("offer_unknown", "unknown") and price.get("amount") is not None:
            errors.append(f"observations[{index}]: unknown sale amount must be null")
        if row.get("best_offer") is True and price.get("basis") != "offer_unknown":
            errors.append(f"observations[{index}]: Best Offer is not a known sale price")
        if row.get("best_offer") not in (True, False) and price.get("basis") == "sold_display":
            errors.append(f"observations[{index}]: offer detection was not verified")
        if price.get("basis") == "sold_display" and positive(price.get("amount")) is None:
            errors.append(f"observations[{index}]: invalid sold price")
        shipping = row.get("shipping", {})
        if shipping.get("basis") == "unknown" and shipping.get("amount") is not None:
            errors.append(f"observations[{index}]: unknown shipping must not become zero")
        if shipping.get("basis") == "free_display" and str(shipping.get("amount")) not in ("0", "0.0", "0.00"):
            errors.append(f"observations[{index}]: free shipping amount must be zero")
        if not reasons:
            buckets[cid].append(row)
        counts[cid][status] += 1
        audits.append({"row": index, "candidate_id": cid, "item_id": row.get("item_id"),
                       "status": status, "reasons": reasons})
    summary = {}
    for cid, accepted in buckets.items():
        all_stats = stats(accepted)
        # 同じ売り手・日付・価格の別IDは再出品等の可能性を残す。
        overlaps = Counter((r["seller"], r["sold_date"], r["price"].get("amount")) for r in accepted)
        summary[cid] = {
            "counts": dict(counts[cid]), "window": all_stats,
            "recent_7d": stats([r for r in accepted if date.fromisoformat(r["sold_date"]) >= recent_start]),
            "possible_same_seller_day_price_groups": sum(n > 1 for n in overlaps.values()),
            "demand_minimum_met": (all_stats["records"] >= criteria["min_records"]
                                   and all_stats["sellers"] >= criteria["min_sellers"]
                                   and all_stats["days"] >= criteria["min_days"]),
        }
    return summary, audits, errors


def validate(path):
    path = Path(path).resolve()
    record = json.loads(path.read_text(encoding="utf-8-sig"))
    errors, issues, summaries, audits = [], [], {}, []

    def verify_file(ref, label):
        if not isinstance(ref, dict) or not ref.get("path") or not ref.get("sha256"):
            errors.append(label + ": path and sha256 required")
            return None
        target = (path.parent / ref["path"]).resolve()
        if not target.is_file():
            errors.append(label + ": file missing")
            return None
        if digest(target) != ref["sha256"]:
            errors.append(label + ": sha256 mismatch")
            return None
        return target

    try:
        if record.get("stage") != 2 or record.get("schema_version") != "1.0":
            errors.append("stage/schema_version mismatch")
        if record.get("execution_mode") not in ("step_by_step", "full_production"):
            errors.append("execution_mode invalid")
        observed = timestamp(record["observed_at"])
        start, end = (date.fromisoformat(record["window"][k]) for k in ("start", "end"))
        if not start <= end < observed.date() or not record["window"].get("date_basis"):
            errors.append("window must be completed dates with date_basis")
        criteria = record["criteria"]
        if criteria.get("market_proxy") != "seller_country":
            errors.append("this checker supports only the declared seller_country proxy")
        for key in ("min_records", "min_sellers", "min_days"):
            if not isinstance(criteria[key], int) or criteria[key] < 1:
                errors.append(key + ": positive integer required")
        for key in ("max_price_age_hours", "max_demand_age_hours"):
            if positive(criteria[key]) is None:
                errors.append(key + ": positive number required")
        if not record.get("scope_authorization"):
            errors.append("scope_authorization required")
        intake = verify_file(record.get("intake"), "intake")
        if intake:
            previous = json.loads(intake.read_text(encoding="utf-8-sig"))
            if previous.get("stage") != 1 or previous.get("handoff", {}).get("ready_for_selection") is not True:
                errors.append("intake is not ready for selection")
        source_list = record["sources"]
        sources = {s["id"]: s for s in source_list}
        if len(sources) != len(source_list):
            errors.append("duplicate source id")
        fresh_primary = set()
        stale_prices = set()
        for source in source_list:
            verify_file(source, "source " + source["id"])
            age = (observed - timestamp(source["retrieved_at"])).total_seconds() / 3600
            if age < 0 or not source.get("url") or not source.get("method"):
                errors.append("source time/url/method invalid: " + source["id"])
            if source["kind"] in PRIMARY and 0 <= age <= criteria["max_demand_age_hours"]:
                fresh_primary.add(source["id"])
            if source["kind"] in ("asking_price", "exchange_rate") and age > criteria["max_price_age_hours"]:
                stale_prices.add(source["id"])
        sites = {s["site"] for s in record.get("site_checks", []) if s.get("result") and s.get("source_ids")}
        if not {"snkrdunk", "ebay", "tcgplayer", "amazon_jp"} <= sites:
            errors.append("four site checks or unavailable reasons required")
        for check in record.get("site_checks", []):
            if any(s not in sources for s in check.get("source_ids", [])):
                errors.append("site check references unknown source")
        candidate_ids = [c["id"] for c in record["candidates"]]
        if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            errors.append("candidate ids empty or duplicated")
        for candidate in record["candidates"]:
            if not candidate.get("decision_reason"):
                errors.append("candidate needs adoption/rejection reason: " + candidate["id"])
        observations = verify_file(record.get("observations"), "observations")
        rows = []
        if observations:
            rows = json.loads(observations.read_text(encoding="utf-8-sig"))
            summaries, audits, row_errors = aggregate(record, rows, sources)
            errors.extend(row_errors)
        selected = record.get("selected_id")
        if selected is None:
            issues.append("no product selected")
        elif selected not in summaries:
            errors.append("selected_id has no candidate/observations")
        else:
            if not summaries[selected]["demand_minimum_met"]:
                issues.append("selected product lacks multiple independent sold observations")
            accepted = {a["row"] for a in audits if a["candidate_id"] == selected and a["status"] == "included"}
            if any(rows[i]["source_id"] not in fresh_primary for i in accepted):
                issues.append("selected demand evidence requires refresh")
        decision = record["decision"]
        for field in ("reason", "buyer_benefit", "facts_allowed", "claims_not_allowed", "constraints_carried_forward"):
            if not decision.get(field):
                errors.append("decision missing: " + field)
        if decision.get("buyer_benefit_status") not in ("verified", "conditional_quote"):
            issues.append("buyer benefit is not established even conditionally")
        if decision.get("buyer_benefit_status") == "conditional_quote":
            if not decision.get("quote_conditions") or not decision.get("unresolved"):
                errors.append("conditional benefit needs explicit conditions and unresolved items")
        if not decision.get("economic_source_ids"):
            issues.append("no sources for buyer benefit")
        for sid in decision.get("economic_source_ids", []):
            if sid not in sources:
                errors.append("unknown economic source: " + sid)
            if sid in stale_prices:
                issues.append("economic reference price requires refresh: " + sid)
        handoff = record["handoff"]
        if handoff.get("next_stage") != 3:
            errors.append("handoff must target stage 3")
        if record.get("execution_mode") == "step_by_step" and handoff.get("stop_after_this_stage") is not True:
            errors.append("step_by_step requires stop_after_this_stage")
        if handoff.get("ready_for_copy") is True and (issues or errors):
            errors.append("declared ready_for_copy contradicts evidence or record")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        errors.append("invalid schema: " + str(exc))
    ready = not errors and not issues and record.get("handoff", {}).get("ready_for_copy") is True
    return {
        "record_valid": not errors, "ready_for_copy": ready,
        "continue_now": ready and record.get("execution_mode") == "full_production"
                        and not record.get("handoff", {}).get("stop_after_this_stage"),
        "errors": errors, "readiness_issues": issues,
        "candidate_metrics": summaries, "row_audit": audits,
        "limits": "ファイル・整合性・標本の検査。原本の真偽、品質、利益、人気、文章品質、広告公開可否を自動認定しない。",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.record)
    except (OSError, ValueError) as exc:
        result = {"record_valid": False, "ready_for_copy": False, "continue_now": False, "errors": [str(exc)]}
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("row_audit",)}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["record_valid"] else 1)


if __name__ == "__main__":
    main()
