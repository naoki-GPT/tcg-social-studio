"""v1.0: 公開ページ・画像を取得し、取得時点と出典を保存する。内部APIは使わない。"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
PAGE_LIMIT = 5 * 1024 * 1024
IMAGE_LIMIT = 15 * 1024 * 1024


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def public_url(value):
    # この道具は外部公開URLだけを扱う。ローカルファイル・認証付きURLは拒否する。
    u = urllib.parse.urlsplit(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        raise ValueError("認証情報を含まないHTTPSの公開URLを指定してください")
    if u.hostname.lower() in {"localhost", "localhost.localdomain"} or u.hostname.endswith(".local"):
        raise ValueError("ローカル端末のURLは取得しません")
    try:
        addr = ipaddress.ip_address(u.hostname)
    except ValueError:
        pass
    else:
        if not addr.is_global:
            raise ValueError("非公開ネットワークのIPアドレスは取得しません")
    return value


class Page(HTMLParser):
    """見出しに紐づくリンク・本文・画像だけを抽出。スクリプトは実行しない。"""

    def __init__(self, url):
        super().__init__(convert_charrefs=True)
        self.url, self.text, self.links, self.images, self.meta = url, [], [], [], {}
        self.skip = 0
        self.heading_tag = None
        self.heading_parts = []
        self.section = ""
        self.anchor = None
        self.title_parts = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style", "noscript", "template"):
            self.skip += 1
        if self.skip:
            return
        if tag == "title":
            self.in_title = True
        if tag in ("h1", "h2", "h3", "h4"):
            self.heading_tag, self.heading_parts = tag, []
        if tag == "a" and a.get("href"):
            self.anchor = {"url": urllib.parse.urljoin(self.url, a["href"]),
                           "section": self.section, "parts": []}
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key and a.get("content"):
                self.meta[key] = a["content"]
        if tag == "img":
            src = a.get("src") or a.get("data-src")
            if src and not src.startswith("data:"):
                self.images.append({"url": urllib.parse.urljoin(self.url, src),
                                    "alt": a.get("alt", "")})
        if tag in ("p", "li", "br", "div", "tr", "h1", "h2", "h3", "h4"):
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self.skip:
            self.skip -= 1
            return
        if self.skip:
            return
        if tag == "title":
            self.in_title = False
        if tag == self.heading_tag:
            self.section = " ".join(self.heading_parts).strip()
            self.heading_tag = None
        if tag == "a" and self.anchor:
            self.anchor["text"] = " ".join(self.anchor.pop("parts")).strip()
            self.links.append(self.anchor)
            self.anchor = None

    def handle_data(self, data):
        if self.skip:
            return
        s = re.sub(r"\s+", " ", data).strip()
        if not s:
            return
        self.text.append(s + " ")
        if self.in_title:
            self.title_parts.append(s)
        if self.heading_tag:
            self.heading_parts.append(s)
        if self.anchor:
            self.anchor["parts"].append(s)

    def result(self):
        body = re.sub(r"[ \t]+", " ", "".join(self.text))
        body = re.sub(r"\n\s*\n+", "\n", body).strip()
        # 人気順の意味を売上順位へ変換しない。リンク自体を保存する。
        ranking = [x for x in self.links
                   if "人気" in x["section"] and "/apparels/" in x["url"]]
        # 関連商品内の数値の場合もあるため、機械抽出したsoldは必ず未検証扱い。
        matches = re.findall(r".{0,70}\b\d[\d,]*\s+sold\b.{0,70}", body, re.I)
        return {"title": " ".join(self.title_parts), "meta": self.meta,
                "text": body, "images": self.images, "links": self.links,
                "popularity_links": ranking,
                "tcg_popularity_links": [x for x in ranking if "トレカ" in x["section"]],
                "unverified_sold_matches": matches[:20],
                "warning": "人気順位・出品価格・定義不明の数値を成約件数に読み替えない。soldの一致箇所は商品本文との照合が必要。"}


def read_url(url, limit):
    req = urllib.request.Request(public_url(url), headers={
        "User-Agent": "Mozilla/5.0", "Accept-Language": "ja,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        public_url(r.url)
        raw = r.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("取得サイズが上限を超えました")
        return raw, r.headers, r.url, r.status


def classify_page(url, result):
    if re.search(r"pardon our interruption|access denied|just a moment|robot check", result["title"], re.I):
        return "blocked"
    u = urllib.parse.urlsplit(url)
    if u.hostname == "jp.mercari.com":
        if "/search" in u.path and not any("/item/" in x["url"] for x in result["links"]):
            return "shell_only"
        if "/item/" in u.path and "商品の説明" not in result["text"]:
            return "shell_only"
    if u.hostname == "snkrdunk.com" and "/used/" in u.path:
        if "購入手数料" not in result["text"] and "商品の状態" not in result["text"]:
            return "shell_only"
    return "fetched"


def collect_page(url, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    record = {"url": url, "observed_at": now(), "method": "public_html_get"}
    try:
        raw, headers, final_url, status = read_url(url, PAGE_LIMIT)
        if "html" not in headers.get("Content-Type", "").lower():
            raise ValueError("HTMLページではありません")
        html = raw.decode(headers.get_content_charset() or "utf-8", errors="replace")
        p = Page(final_url)
        p.feed(html)
        result = p.result()
        # 検索・商品ページの外枠しかないHTMLを商品取得成功にしない。
        page_status = classify_page(final_url, result)
        original_id = re.search(r"/itm/(\d+)", url)
        final_id = re.search(r"/itm/(\d+)", final_url)
        identity_preserved = (not original_id or bool(final_id and original_id[1] == final_id[1]))
        record.update({"status": page_status,
                       "primary_item_identity_preserved": identity_preserved,
                       "http_status": status, "final_url": final_url,
                       "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                       **result})
        (out / "page.html").write_bytes(raw)
        (out / "page.txt").write_text(result["text"], encoding="utf-8")
    except (OSError, ValueError) as e:
        record.update({"status": "failed", "error": str(e)})
    write_json(out / "snapshot.json", record)
    print(json.dumps({k: record[k] for k in ("url", "observed_at", "status")}, ensure_ascii=False))
    return record["status"] == "fetched"


def collect_image(url, out):
    out = Path(out)
    if out.exists() or out.with_suffix(out.suffix + ".source.json").exists():
        raise FileExistsError("既存の画像・出典を上書きしません")
    raw, headers, final_url, status = read_url(url, IMAGE_LIMIT)
    mime = headers.get("Content-Type", "").split(";")[0]
    if mime not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        raise ValueError(f"対応する画像形式ではありません: {mime}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("xb") as f:
        f.write(raw)
    record = {"url": url, "final_url": final_url, "observed_at": now(),
              "method": "public_image_get", "http_status": status,
              "mime": mime, "bytes": len(raw), "path": str(out.resolve()),
              "sha256": hashlib.sha256(raw).hexdigest()}
    write_json(out.with_suffix(out.suffix + ".source.json"), record)
    print(json.dumps(record, ensure_ascii=False))
    return True


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=("page", "image"))
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    try:
        ok = collect_page(a.url, a.out) if a.kind == "page" else collect_image(a.url, a.out)
    except (OSError, ValueError) as e:
        print(f"[ERROR] {e}")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
