"""v1.0.0: 前提記録の根拠参照・企画数・引き渡し条件を検査する（オフライン）。

需要・価格の真偽や実際のアクセス履歴を検証するものではない。
終了コード: 0=次工程の調査条件がそろった、2=記録不備、3=重要な前提が未決。
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

FIELDS = (
    "project", "audience", "market", "objective", "primary_action",
    "concept_count", "product_scope", "media_format", "copy_language",
    "destination", "reference", "sales_terms",
)
REQUIRED = FIELDS[:7]
STATUSES = {"confirmed", "proposed", "unknown", "deferred"}


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate(data):
    errors, blockers, assumptions = [], [], []
    if not isinstance(data, dict):
        return {"record_valid": False, "ready_for_selection": False,
                "continue_now": False, "errors": ["記録の最上位はオブジェクトが必要"],
                "blockers": [], "assumptions": []}

    if data.get("schema_version") != "1.0" or type(data.get("stage")) is not int or data["stage"] != 1:
        errors.append("schema_version=1.0、stage=1が必要")
    try:
        date.fromisoformat(data.get("recorded_on", ""))
    except (TypeError, ValueError):
        errors.append("recorded_onは実際の記録日YYYY-MM-DDが必要")
    mode = data.get("execution_mode")
    if mode not in ("step_by_step", "full_production"):
        errors.append("execution_modeが不正")

    sources = data.get("sources")
    if not isinstance(sources, list):
        sources = []
        errors.append("sourcesは配列が必要")
    ids = set()
    for item in sources:
        if not isinstance(item, dict):
            errors.append("sourcesの要素はオブジェクトが必要")
            continue
        sid = item.get("id")
        if not nonempty(sid) or sid in ids:
            errors.append("根拠IDが空または重複")
            continue
        ids.add(sid)
        for key in ("kind", "locator", "excerpt", "checked_on"):
            if not nonempty(item.get(key)):
                errors.append(f"根拠 {sid}: {key} が必要")

    def check_refs(item, label, required=False):
        refs = item.get("source_ids")
        if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
            errors.append(f"{label}: source_idsは文字列配列が必要")
        elif (required and not refs) or any(x not in ids for x in refs):
            errors.append(f"{label}: 読んだ根拠IDへの参照が必要")

    brief = data.get("brief")
    if not isinstance(brief, dict):
        brief = {}
        errors.append("briefはオブジェクトが必要")
    for key in FIELDS:
        item = brief.get(key)
        if not isinstance(item, dict):
            errors.append(f"{key}: 項目がない")
            if key in REQUIRED:
                blockers.append(key)
            continue
        state, value = item.get("status"), item.get("value")
        if not isinstance(state, str) or state not in STATUSES:
            errors.append(f"{key}: 状態が不正")
            if key in REQUIRED:
                blockers.append(key)
            continue
        check_refs(item, key, required=state == "confirmed")
        if not nonempty(item.get("note")):
            errors.append(f"{key}: 判断理由・適用範囲のnoteが必要")
        if state in {"confirmed", "proposed"}:
            if key == "concept_count":
                if type(value) is not int or value < 1:
                    errors.append("concept_count: 企画数は正の整数が必要")
            elif not nonempty(value):
                errors.append(f"{key}: 決定・提案した値が必要")
        if state in {"unknown", "deferred"} and value is not None:
            errors.append(f"{key}: 未決の値はnullにし、既知の部分はnoteへ")
        if state == "deferred":
            at = item.get("resolve_at_stage")
            if type(at) is not int or not 2 <= at <= 7:
                errors.append(f"{key}: 後で決める工程番号2〜7が必要")
        if state == "proposed":
            assumptions.append(key)
        if key in REQUIRED and state not in {"confirmed", "proposed"}:
            blockers.append(key)
        if key in {"project", "concept_count"} and state != "confirmed":
            if key not in blockers:
                blockers.append(key)

    for key in ("constraints", "resource_access", "rejected_candidates", "open_questions"):
        items = data.get(key)
        if not isinstance(items, list):
            errors.append(f"{key}: 配列が必要")
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{key}[{i}]: オブジェクトが必要")
                continue
            check_refs(item, f"{key}[{i}]", required=key != "open_questions")
            if key == "resource_access":
                if not nonempty(item.get("resource")):
                    errors.append("resource_access: 対象名が必要")
                if type(item.get("read")) is not bool or type(item.get("write")) is not bool:
                    errors.append("resource_access: read/writeは真偽値が必要")
            elif key == "open_questions" and item.get("blocks_selection") is True:
                blockers.append(item.get("question", f"open_questions[{i}]"))

    handoff = data.get("handoff")
    if not isinstance(handoff, dict):
        handoff = {}
        errors.append("handoffが必要")
    if handoff.get("next_stage") != 2 or not nonempty(handoff.get("instructions")):
        errors.append("handoff: 次は第2工程。引き渡す具体的な指示が必要")
    if handoff.get("stop_after_this_stage") is not (mode == "step_by_step"):
        errors.append("handoff: 工程ごとの依頼はここで停止する")
    if handoff.get("ready_for_selection") is not (not blockers and not errors):
        errors.append("handoff: ready_for_selectionが根拠・未決事項と一致しない")
    ready = not errors and not blockers
    return {"record_valid": not errors, "ready_for_selection": ready,
            "continue_now": ready and mode == "full_production",
            "errors": errors, "blockers": blockers, "assumptions": assumptions}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    try:
        result = validate(json.loads(args.record.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError) as exc:
        result = {"record_valid": False, "ready_for_selection": False,
                  "continue_now": False, "errors": [str(exc)], "blockers": [], "assumptions": []}
    result["scope"] = "記録の構造・根拠参照・引き渡し条件のみ。真偽・アクセス履歴・制作品質は人による照合が必要。"
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 2 if result["errors"] else (0 if result["ready_for_selection"] else 3)


if __name__ == "__main__":
    raise SystemExit(main())
