"""v1.0: 既存strip_metadata.pyと同じ画素コピー方式。JPEG付加セグメント検査を追加。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
from pathlib import Path
import sys

from PIL import Image, ImageOps


def jpeg_segments(path):
    """画像データの前にあるJPEGセグメントを読む。撮影情報の値自体は出力しない。"""
    raw = Path(path).read_bytes()
    if raw[:2] != b"\xff\xd8":
        raise ValueError("JPEGではありません")
    i, segments = 2, []
    while i < len(raw):
        if raw[i] != 0xFF:
            raise ValueError("JPEGのマーカーが不正です")
        while raw[i] == 0xFF:
            i += 1
        marker = raw[i]
        i += 1
        if marker in (0xDA, 0xD9):  # 画像本体、または終端
            break
        length = int.from_bytes(raw[i:i + 2], "big")
        if length < 2 or i + length > len(raw):
            raise ValueError("JPEGの長さが不正です")
        payload = raw[i + 2:i + length]
        segments.append((marker, payload))
        i += length
    return segments


def inspect(path):
    with Image.open(path) as im:
        im.load()
        result = {"size": list(im.size), "mode": im.mode,
                  "exif_tag_count": len(im.getexif()),
                  "info_keys": sorted(im.info.keys())}
    # APP0のJFIFは画像形式の識別情報。EXIF/XMP/ICC/IPTC/C2PA等のAPP1-15とCOMは許可しない。
    bad = []
    for marker, payload in jpeg_segments(path):
        if 0xE1 <= marker <= 0xEF or marker == 0xFE:
            bad.append(f"0x{marker:02X}")
        elif marker == 0xE0 and not payload.startswith(b"JFIF\x00"):
            bad.append("APP0(non-JFIF)")
    result["unexpected_metadata_segments"] = bad
    result["passed"] = not bad and result["exif_tag_count"] == 0 and set(result["info_keys"]) <= {
        "jfif", "jfif_version", "jfif_unit", "jfif_density"}
    return result


def clean(src, out, report):
    src, out, report = Path(src), Path(out), Path(report)
    if src.resolve() == out.resolve() or out.exists() or report.exists():
        raise FileExistsError("元画像と既存の成果物を上書きしません")
    with Image.open(src) as im:
        im.load()
        before = {"size": list(im.size), "info_keys": sorted(im.info.keys()),
                  "exif_tag_count": len(im.getexif())}
        im = ImageOps.exif_transpose(im)
        icc = im.info.get("icc_profile")
        if icc:
            # 色変換に失敗したままICCだけ外すと色が変わるため、失敗時は停止する。
            from PIL import ImageCms
            im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                           ImageCms.createProfile("sRGB"), outputMode="RGB")
        rgba = im.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("xb") as f:
            canvas.save(f, "JPEG", quality=95, optimize=True)
    after = inspect(out)
    result = {"version": "1.0", "checked_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
              "source": str(src.resolve()), "output": str(out.resolve()),
              "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
              "output_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
              "before": before, "after": after,
              "method": "orientation/sRGB, fresh pixels, JPEG95, no noise, no fabricated EXIF"}
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    if not after["passed"]:
        raise ValueError("付加情報が残っています。検査記録を確認してください")
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    try:
        r = clean(a.src, a.out, a.report)
    except (OSError, ValueError) as e:
        print(f"[ERROR] {e}")
        return 1
    print(f"[OK] メタデータ検査成功: {r['output']} ({r['after']['size']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
