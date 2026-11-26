"""Tải Short lên YouTube bằng YouTube Data API và hẹn giờ công khai.

Một lần đầu:  .venv/bin/python dang_ytb.py dang-nhap      (mở trình duyệt, đăng nhập tài khoản có kênh)
Đăng:         .venv/bin/python dang_ytb.py dang kich-ban/2026-11-27.json [--gio 19:30] [--thu]
Xem kênh:     .venv/bin/python dang_ytb.py kenh

Cần file google-oauth.json (OAuth client loại "Desktop app") — xem mục 8 HUONG-DAN.md.
LƯU Ý: khi project Google Cloud CHƯA qua audit của YouTube, mọi video tải lên qua API đều bị
khoá ở chế độ Riêng tư. Đặt "ytb_api_da_duyet": true trong cau-hinh.json sau khi được duyệt.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

GOC = Path(__file__).resolve().parent
CLIENT = GOC / "google-oauth.json"
TOKEN = GOC / ".ytb-token.json"
PHAM_VI = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube.readonly"]
MUI_GIO = ZoneInfo("Asia/Ho_Chi_Minh")
DANH_MUC_KHOA_HOC_CONG_NGHE = "28"


class LoiDang(Exception):
    pass


def cau_hinh() -> dict:
    p = GOC / "cau-hinh.json"
    ch = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return {"gio_dang": ch.get("gio_dang", "19:30"), "ytb_api_da_duyet": ch.get("ytb_api_da_duyet", False)}


def _creds(cho_phep_dang_nhap=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(TOKEN), PHAM_VI) if TOKEN.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception as e:  # refresh token hết hạn / bị thu hồi
            if not cho_phep_dang_nhap:
                raise LoiDang(f"Phiên đăng nhập YouTube hết hạn ({e}). Chạy lại: .venv/bin/python dang_ytb.py dang-nhap")
    if not cho_phep_dang_nhap:
        raise LoiDang("Chưa đăng nhập YouTube. Chạy trên máy: .venv/bin/python dang_ytb.py dang-nhap")
    if not CLIENT.exists():
        raise LoiDang(f"Thiếu {CLIENT.name}. Làm theo mục 8 trong HUONG-DAN.md để tạo OAuth client.")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), PHAM_VI)
    creds = flow.run_local_server(port=0, prompt="consent", open_browser=True)
    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    TOKEN.chmod(0o600)
    return creds


def _yt(cho_phep_dang_nhap=False):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_creds(cho_phep_dang_nhap), cache_discovery=False)


def kenh(cho_phep_dang_nhap=False) -> dict:
    r = _yt(cho_phep_dang_nhap).channels().list(part="snippet", mine=True).execute()
    if not r.get("items"):
        raise LoiDang("Tài khoản vừa đăng nhập không có kênh YouTube nào")
    sn = r["items"][0]["snippet"]
    return {"id": r["items"][0]["id"], "ten": sn["title"], "handle": sn.get("customUrl", "")}


def gio_cong_khai(gio: str, bay_gio: datetime | None = None) -> datetime:
    """Hôm nay lúc `gio` (giờ VN). Nếu đã qua hoặc còn dưới 15 phút: 15 phút tới, làm tròn lên mốc 15 phút."""
    bay_gio = bay_gio or datetime.now(MUI_GIO)
    h, m = (int(x) for x in gio.split(":"))
    t = bay_gio.replace(hour=h, minute=m, second=0, microsecond=0)
    if t - bay_gio >= timedelta(minutes=15):
        return t
    t = bay_gio + timedelta(minutes=15)
    return (t + timedelta(minutes=(-t.minute) % 15)).replace(second=0, microsecond=0)


def dang(duong_dan_kb: Path, gio: str | None = None, thu: bool = False, lai: bool = False, tien_do=None) -> dict:
    """Tải video của kịch bản lên YouTube. Trả về {id, link, cong_khai_luc | None, rieng_tu_bi_khoa}."""
    from googleapiclient.http import MediaFileUpload

    ch = cau_hinh()
    duong_dan_kb = Path(duong_dan_kb)
    ngay = duong_dan_kb.stem
    video = GOC / "xuat" / f"{ngay}.mp4"
    da_dang = GOC / "xuat" / f"{ngay}-ytb.json"
    if not video.exists():
        raise LoiDang(f"Chưa có video xuat/{ngay}.mp4")
    if da_dang.exists() and not lai and not thu:
        cu = json.loads(da_dang.read_text(encoding="utf-8"))
        raise LoiDang(f"Video {ngay} đã được tải lên rồi: {cu['link']} (gõ /dang lai nếu chắc chắn muốn tải thêm bản nữa)")
    if not ch["ytb_api_da_duyet"] and not thu:
        raise LoiDang("Project YouTube API chưa được Google duyệt, video tải lên sẽ bị khoá Riêng tư, không công khai được. "
                      "Gõ /dang thu nếu chỉ muốn thử tải lên (Riêng tư). Sau khi được duyệt, đặt "
                      "\"ytb_api_da_duyet\": true trong cau-hinh.json.")

    kb = json.loads(duong_dan_kb.read_text(encoding="utf-8"))
    d = kb.get("dang", {})
    the = [h.lstrip("#") for h in d.get("hashtag", []) if h.lstrip("#").lower() != "shorts"]
    mo_ta = (d.get("mo_ta", "") + "\n\n" + " ".join(d.get("hashtag", []))).strip()
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True,
              "embeddable": True}
    luc = None
    if not thu:
        luc = gio_cong_khai(gio or ch["gio_dang"])
        status["publishAt"] = luc.isoformat()
    body = {
        "snippet": {"title": d.get("tieu_de", ngay)[:100], "description": mo_ta[:5000], "tags": the,
                    "categoryId": DANH_MUC_KHOA_HOC_CONG_NGHE, "defaultLanguage": "vi", "defaultAudioLanguage": "vi"},
        "status": status,
    }
    yt = _yt()
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), mimetype="video/mp4", chunksize=-1, resumable=True))
    res = None
    while res is None:
        st, res = req.next_chunk()
        if st and tien_do:
            tien_do(int(st.progress() * 100))
    vid = res["id"]
    kq = {"id": vid, "link": f"https://youtube.com/shorts/{vid}",
          "cong_khai_luc": luc.isoformat() if luc else None,
          "rieng_tu_bi_khoa": not ch["ytb_api_da_duyet"], "tai_len_luc": datetime.now(MUI_GIO).isoformat()}
    if not thu:  # bản thử không đánh dấu "đã đăng", để /dang thật vẫn chạy được
        da_dang.write_text(json.dumps(kq, ensure_ascii=False, indent=2), encoding="utf-8")
    return kq


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="lenh", required=True)
    sub.add_parser("dang-nhap", help="Đăng nhập Google (lần đầu hoặc khi hết hạn)")
    sub.add_parser("kenh", help="Xem kênh đang đăng nhập")
    p = sub.add_parser("dang", help="Tải video lên và hẹn giờ công khai")
    p.add_argument("kich_ban", type=Path)
    p.add_argument("--gio", help="Giờ công khai HH:MM (mặc định gio_dang trong cau-hinh.json, 19:30)")
    p.add_argument("--thu", action="store_true", help="Chỉ tải lên ở chế độ Riêng tư, không hẹn giờ")
    p.add_argument("--lai", action="store_true", help="Tải lại dù hôm nay đã tải")
    a = ap.parse_args()
    try:
        if a.lenh == "dang-nhap":
            k = kenh(cho_phep_dang_nhap=True)
            print(f"Đã đăng nhập kênh: {k['ten']} {k['handle']}")
        elif a.lenh == "kenh":
            k = kenh()
            print(f"{k['ten']} {k['handle']} ({k['id']})")
        else:
            kq = dang(a.kich_ban, a.gio, a.thu, a.lai, tien_do=lambda p: print(f"  tải lên {p}%"))
            print(json.dumps(kq, ensure_ascii=False, indent=2))
    except LoiDang as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
