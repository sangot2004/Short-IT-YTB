"""Bot Telegram nghe lệnh để làm video Shorts bản tin IT.

Chạy tay:   .venv/bin/python bot.py
Chạy nền:   ./bot-nen bat   (tự khởi động cùng máy; ./bot-nen tat để tắt)

Chỉ trả lời đúng chat có id = TELEGRAM_CHAT_ID trong .env; mọi người khác bị bỏ qua.
"""
import json
import os
import re
import shutil
import subprocess
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import socket

import requests
import urllib3.util.connection as _u

import ban_tin

# Khi chạy nền, kết nối IPv6 tới Telegram có thể treo: chỉ dùng IPv4.
_u.allowed_gai_family = lambda: socket.AF_INET

GOC = Path(__file__).resolve().parent
PY = str(GOC / ".venv" / "bin" / "python")
NHAT_KY = GOC / "tam" / "bot.log"

LENH = [
    ("lam", "Làm video hôm nay (có rồi thì gửi lại)"),
    ("lam_moi", "Viết kịch bản MỚI cho hôm nay rồi làm video"),
    ("sua", "Sửa kịch bản hôm nay: /sua <yêu cầu>"),
    ("tin", "Xem 15 tin IT mới nhất"),
    ("giong", "Xem/đổi giọng đọc: /giong Mai Anh"),
    ("dang", "Tải video hôm nay lên YouTube, hẹn công khai 19:30 (/dang 20:00 để đổi giờ)"),
    ("trang_thai", "Bot đang làm gì"),
    ("help", "Danh sách lệnh"),
]

_ban = threading.Lock()
_viec_hien_tai = {"ten": None, "tu": None}


# ---------------------------------------------------------------- tiện ích
def ghi_log(*a):
    NHAT_KY.parent.mkdir(exist_ok=True)
    dong = f"{datetime.now():%Y-%m-%d %H:%M:%S} " + " ".join(str(x) for x in a)
    dong = re.sub(r"bot\d+:[\w-]+", "bot<token>", dong)  # không ghi token vào nhật ký
    print(dong, flush=True)
    with open(NHAT_KY, "a", encoding="utf-8") as f:
        f.write(dong + "\n")


def env():
    return ban_tin.doc_env()


def api(phuong_thuc, **kw):
    token = env()["TELEGRAM_BOT_TOKEN"]
    r = requests.post(f"https://api.telegram.org/bot{token}/{phuong_thuc}", timeout=(10, kw.pop("timeout", 70)), **kw)
    return r.json()


def nhan(text):
    chat = env()["TELEGRAM_CHAT_ID"]
    for i in range(0, len(text), 3900):
        api("sendMessage", data={"chat_id": chat, "text": text[i:i + 3900], "disable_web_page_preview": "true"})


def hom_nay():
    return datetime.now().strftime("%Y-%m-%d")


def file_kb(ngay=None):
    return GOC / "kich-ban" / f"{ngay or hom_nay()}.json"


def tim_claude():
    p = shutil.which("claude")
    if p:
        return p
    for g in sorted(Path.home().glob(".nvm/versions/node/*/bin/claude"), reverse=True):
        return str(g)
    raise RuntimeError("Không tìm thấy lệnh claude")


# ---------------------------------------------------------------- các bước
def lay_tin():
    subprocess.run([PY, "lay_tin.py"], cwd=GOC, check=True, capture_output=True, timeout=180)
    return GOC / "tin" / f"{hom_nay()}.md"


def goi_claude(them: str, ra: Path, tin: Path) -> str:
    mau = (GOC / "prompt-viet-kich-ban.md").read_text(encoding="utf-8")
    prompt = (mau.replace("{TIN}", str(tin.relative_to(GOC)))
                 .replace("{RA}", str(ra.relative_to(GOC)))
                 .replace("{THEM}", them or ""))
    model = ban_tin.doc_cau_hinh().get("model_claude", "sonnet")
    lenh = [tim_claude(), "-p", prompt, "--model", model, "--output-format", "text",
            "--allowedTools", "Read", "Glob", "Grep", "Write(./kich-ban/**)", "Edit(./kich-ban/**)",
            "--disallowedTools", "Bash", "WebFetch", "WebSearch"]
    moi_truong = dict(os.environ)
    moi_truong["PATH"] = str(Path(lenh[0]).parent) + ":" + moi_truong.get("PATH", "/usr/bin:/bin")
    kq = subprocess.run(lenh, cwd=GOC, capture_output=True, text=True, timeout=900, env=moi_truong)
    if kq.returncode:
        raise RuntimeError(f"Claude lỗi: {(kq.stderr or kq.stdout)[-500:]}")
    return kq.stdout.strip()


def kiem_tra_kb(p: Path):
    if not p.exists():
        raise RuntimeError("Claude không tạo file kịch bản")
    kb = json.loads(p.read_text(encoding="utf-8"))
    if not kb.get("canh"):
        raise RuntimeError("Kịch bản không có cảnh nào")
    for i, c in enumerate(kb["canh"], 1):
        loai = (c.get("the") or {}).get("loai", "tieu_de")
        if loai not in ban_tin.LOAI_THE:
            raise RuntimeError(f"Cảnh {i}: loại thẻ '{loai}' không hợp lệ")
    return kb


def dung_video(p: Path) -> float:
    kq = subprocess.run([PY, "ban_tin.py", "dung", str(p)], cwd=GOC, capture_output=True, text=True, timeout=900)
    if kq.returncode:
        raise RuntimeError(f"Dựng video lỗi: {(kq.stderr or kq.stdout)[-600:]}")
    m = re.search(r"tổng: ([\d.]+)s", kq.stdout)
    return float(m.group(1)) if m else 0.0


def viet_va_dung(p: Path, them: str):
    """Gọi Claude viết/sửa kịch bản, kiểm tra, dựng; tự sửa 1 lần nếu lỗi hoặc quá dài."""
    tin = GOC / "tin" / f"{hom_nay()}.md"
    if not tin.exists():
        nhan("📰 Đang lấy tin…")
        tin = lay_tin()
    nhan("✍️ Claude đang viết kịch bản…")
    tra_loi = goi_claude(them, p, tin)
    for lan in range(2):
        try:
            kiem_tra_kb(p)
            nhan("🎙 Đang tạo giọng và dựng video…")
            dai = dung_video(p)
            if dai > 62 and lan == 0:
                nhan(f"⏱ Video dài {dai:.0f} giây, đang rút gọn…")
                tra_loi = goi_claude(f"Kịch bản trong {p.name} đang làm video dài {dai:.0f} giây. Hãy rút gọn lời đọc "
                                     "để video dưới 60 giây, giữ nguyên các tin.", p, tin)
                continue
            return tra_loi, dai
        except Exception as e:
            if lan == 1:
                raise
            nhan("🔧 Có lỗi, Claude đang sửa…")
            tra_loi = goi_claude(f"Lần trước bị lỗi: {e}. Hãy sửa file {p.name} cho đúng.", p, tin)
    raise RuntimeError("Không dựng được video")


def gui_video(p: Path):
    try:
        ban_tin.gui(p)
    except SystemExit as e:
        raise RuntimeError(str(e))


# ---------------------------------------------------------------- lệnh
def lenh_lam(moi=False):
    p = file_kb()
    if p.exists() and moi:
        cu = p.with_name(f"{p.stem}-cu-{datetime.now():%H%M}.json")
        p.rename(cu)
        nhan(f"📦 Đã lưu kịch bản cũ thành {cu.name}")
    if p.exists():
        if not (GOC / "xuat" / f"{p.stem}.mp4").exists():
            nhan("🎙 Đã có kịch bản hôm nay, đang dựng video…")
            dung_video(p)
        nhan("📤 Gửi video hôm nay (dùng /lam_moi nếu muốn viết lại từ đầu)")
        gui_video(p)
        return
    tra_loi, dai = viet_va_dung(p, "")
    nhan(f"✅ Xong video {dai:.0f} giây.\n{tra_loi}")
    gui_video(p)


def lenh_sua(yeu_cau):
    p = file_kb()
    if not p.exists():
        nhan("Hôm nay chưa có kịch bản. Gõ /lam trước nhé.")
        return
    if not yeu_cau:
        nhan("Gõ kèm yêu cầu, ví dụ:\n/sua bỏ tin số 3, viết hook giật gân hơn")
        return
    shutil.copy(p, p.with_name(f"{p.stem}-truoc-sua-{datetime.now():%H%M}.json"))
    them = (f"ĐÂY LÀ LẦN SỬA: file {p.name} đã có sẵn. Đọc nó rồi sửa theo yêu cầu của người dùng, "
            f"giữ nguyên những phần không được nhắc tới.\nYêu cầu: {yeu_cau}")
    tra_loi, dai = viet_va_dung(p, them)
    nhan(f"✅ Đã sửa, video {dai:.0f} giây.\n{tra_loi}")
    gui_video(p)


def lenh_tin():
    nhan("📰 Đang lấy tin…")
    lay_tin()
    tin = json.loads((GOC / "tin" / f"{hom_nay()}.json").read_text(encoding="utf-8"))
    tin = sorted(tin, key=lambda t: t["ts"], reverse=True)[:15]
    nhan("\n\n".join(f"{i}. {t['tieu_de']}\n   — {t['nguon']}, {t['thoi_gian']}" for i, t in enumerate(tin, 1)))


def lenh_giong(ten):
    from vieneu import Vieneu  # chỉ để lấy danh sách tên
    p_ch = GOC / "cau-hinh.json"
    ch = json.loads(p_ch.read_text(encoding="utf-8")) if p_ch.exists() else {}
    if not ten:
        nhan(f"Giọng hiện tại: {ch.get('giong', ban_tin.CAU_HINH_MAC_DINH['giong'])}\n"
             "Đổi bằng: /giong <tên>\nVí dụ: Minh Đức, Mai Anh (nữ, tin tức), Hải Đăng, Thùy Dung (nữ, miền Nam), "
             "Minh Triết (nam, miền Nam), Quang Sơn (nam, miền Trung)")
        return
    ten_hop_le = [t for _, t in Vieneu().list_preset_voices()]
    khop = [t for t in ten_hop_le if t.lower() == ten.lower()]
    if not khop:
        nhan("Không có giọng này. Các giọng: " + ", ".join(ten_hop_le))
        return
    ch["giong"] = khop[0]
    p_ch.write_text(json.dumps(ch, ensure_ascii=False, indent=2), encoding="utf-8")
    nhan(f"✅ Đã đổi giọng thành {khop[0]}. Áp dụng từ video tiếp theo (/sua hoặc /lam_moi để làm lại ngay).")


def lenh_trang_thai():
    p = file_kb()
    v = GOC / "xuat" / f"{p.stem}.mp4"
    viec = _viec_hien_tai["ten"]
    dang = f"⏳ Đang làm: {viec} (từ {_viec_hien_tai['tu']:%H:%M})" if viec else "💤 Đang rảnh"
    nhan(f"{dang}\nKịch bản hôm nay: {'có' if p.exists() else 'chưa'}\nVideo hôm nay: {'có' if v.exists() else 'chưa'}")


def lenh_dang(doi: str):
    """/dang [HH:MM] [thu] [lai] — tải video hôm nay lên YouTube và hẹn giờ công khai."""
    import dang_ytb

    p = file_kb()
    if not p.exists() or not (GOC / "xuat" / f"{p.stem}.mp4").exists():
        nhan("Hôm nay chưa có video. Gõ /lam trước nhé.")
        return
    tu = doi.lower().split()
    gio = next((t for t in tu if re.fullmatch(r"\d{1,2}:\d{2}", t)), None)
    thu, lai = "thu" in tu, "lai" in tu
    nhan("⬆️ Đang tải video lên YouTube…")
    try:
        kq = dang_ytb.dang(p, gio=gio, thu=thu, lai=lai)
    except dang_ytb.LoiDang as e:
        nhan(f"⚠️ {e}")
        return
    if kq["cong_khai_luc"]:
        luc = datetime.fromisoformat(kq["cong_khai_luc"])
        nhan(f"✅ Đã tải lên và hẹn công khai lúc {luc:%H:%M %d/%m}.\n{kq['link']}\n"
             "Muốn huỷ thì vào YouTube Studio → Nội dung → Shorts, đổi về Riêng tư hoặc xoá.")
    else:
        nhan(f"✅ Đã tải lên ở chế độ Riêng tư (chế độ thử, project API chưa được duyệt nên video bị khoá Riêng tư).\n"
             f"{kq['link']}\nKiểm tra xong thì xoá video thử trong YouTube Studio.")


def lenh_help():
    nhan("Các lệnh:\n" + "\n".join(f"/{l} — {m}" for l, m in LENH))


def chay_nen(ten, ham, *a):
    if not _ban.acquire(blocking=False):
        nhan(f"⏳ Bot đang bận: {_viec_hien_tai['ten']}. Đợi xong rồi gõ lại nhé.")
        return

    def chay():
        _viec_hien_tai.update(ten=ten, tu=datetime.now())
        t0 = time.time()
        try:
            ham(*a)
            ghi_log("xong", ten, f"{time.time() - t0:.0f}s")
        except Exception as e:
            ghi_log("lỗi", ten, traceback.format_exc())
            nhan(f"❌ Lỗi khi {ten}: {e}")
        finally:
            _viec_hien_tai.update(ten=None, tu=None)
            _ban.release()

    threading.Thread(target=chay, daemon=True).start()


def xu_ly(text: str):
    m = re.match(r"^/(\w+)(?:@\w+)?\s*(.*)$", text.strip(), re.S)
    if not m:
        nhan("Gõ /help để xem các lệnh.")
        return
    lenh, doi = m.group(1).lower(), m.group(2).strip()
    if lenh == "lam":
        chay_nen("làm video hôm nay", lenh_lam)
    elif lenh == "lam_moi":
        chay_nen("viết kịch bản mới", lenh_lam, True)
    elif lenh == "sua":
        chay_nen("sửa kịch bản", lenh_sua, doi)
    elif lenh == "tin":
        chay_nen("lấy tin", lenh_tin)
    elif lenh == "giong":
        lenh_giong(doi)
    elif lenh == "dang":
        chay_nen("đăng lên YouTube", lenh_dang, doi)
    elif lenh == "trang_thai":
        lenh_trang_thai()
    else:
        lenh_help()


def main():
    e = env()
    if not e.get("TELEGRAM_BOT_TOKEN") or not e.get("TELEGRAM_CHAT_ID"):
        raise SystemExit("Thiếu TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID trong .env")
    chu = str(e["TELEGRAM_CHAT_ID"])
    api("setMyCommands", data={"commands": json.dumps([{"command": l, "description": m} for l, m in LENH],
                                                      ensure_ascii=False)})
    ghi_log("bot bắt đầu nghe lệnh")
    offset = None
    while True:
        try:
            r = api("getUpdates", params={"timeout": 50, "offset": offset}, timeout=70)
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or {}
                if str(msg.get("chat", {}).get("id")) != chu:
                    continue  # chỉ nghe chủ bot
                text = msg.get("text", "")
                if text:
                    ghi_log("lệnh:", text[:100])
                    xu_ly(text)
        except requests.RequestException as ex:
            ghi_log("mạng lỗi:", ex)
            time.sleep(10)
        except Exception:
            ghi_log("lỗi:", traceback.format_exc())
            time.sleep(5)


if __name__ == "__main__":
    main()
