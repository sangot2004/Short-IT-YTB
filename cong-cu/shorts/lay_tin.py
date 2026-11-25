"""Lấy tin IT mới từ các nguồn RSS và ghi thành một file tóm tắt để viết kịch bản.

Chạy:  .venv/bin/python lay_tin.py [--gio 30]
Kết quả: tin/YYYY-MM-DD.md (danh sách tin, nhóm theo nguồn) và tin/YYYY-MM-DD.json
"""
import argparse
import calendar
import html
import json
import re
import time
from datetime import datetime
from pathlib import Path

import feedparser

GOC = Path(__file__).resolve().parent

NGUON = {
    "VnExpress Số hóa": "https://vnexpress.net/rss/so-hoa.rss",
    "Tuổi Trẻ Nhịp sống số": "https://tuoitre.vn/rss/nhip-song-so.rss",
    "GenK": "https://genk.vn/rss/home.rss",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Hacker News (>200 điểm)": "https://hnrss.org/frontpage?points=200",
}


def lam_sach(s: str, toi_da: int = 350) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(re.sub(r"\s+", " ", s)).strip()
    return s if len(s) <= toi_da else s[:toi_da].rsplit(" ", 1)[0] + "…"


def lay(so_gio: int, moi_nguon: int = 10) -> list[dict]:
    moc = time.time() - so_gio * 3600
    tin, da_co = [], set()
    for ten, url in NGUON.items():
        d = feedparser.parse(url, agent="Mozilla/5.0 (rss-reader)")
        if not d.entries:
            print(f"  ! {ten}: không lấy được ({d.get('bozo_exception')})")
            continue
        dem = 0
        for e in d.entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            ts = calendar.timegm(t) if t else time.time()
            if ts < moc or dem >= moi_nguon:
                continue
            khoa = re.sub(r"\W+", "", e.title.lower())[:60]
            if khoa in da_co:
                continue
            da_co.add(khoa)
            tin.append({
                "nguon": ten,
                "tieu_de": lam_sach(e.title, 200),
                "tom_tat": lam_sach(e.get("summary", "")),
                "link": e.get("link", ""),
                "thoi_gian": datetime.fromtimestamp(ts).strftime("%d/%m %H:%M"),
                "ts": ts,
            })
            dem += 1
        print(f"  {ten}: {dem} tin")
    return tin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gio", type=int, default=30, help="lấy tin trong N giờ gần nhất")
    ap.add_argument("--moi-nguon", type=int, default=10, help="tối đa N tin mỗi nguồn")
    a = ap.parse_args()
    ngay = datetime.now().strftime("%Y-%m-%d")
    thu_muc = GOC / "tin"
    thu_muc.mkdir(exist_ok=True)
    tin = lay(a.gio, a.moi_nguon)
    (thu_muc / f"{ngay}.json").write_text(json.dumps(tin, ensure_ascii=False, indent=1), encoding="utf-8")
    dong = [f"# Tin IT {ngay} ({len(tin)} tin, {a.gio} giờ gần nhất)\n"]
    nguon_truoc = None
    for i, t in enumerate(tin, 1):
        if t["nguon"] != nguon_truoc:
            dong.append(f"\n## {t['nguon']}\n")
            nguon_truoc = t["nguon"]
        dong.append(f"{i}. **{t['tieu_de']}** — {t['nguon']}, {t['thoi_gian']}\n   {t['tom_tat']}\n   {t['link']}\n")
    p = thu_muc / f"{ngay}.md"
    p.write_text("\n".join(dong), encoding="utf-8")
    print(f"Đã ghi {p} ({len(tin)} tin)")


if __name__ == "__main__":
    main()
