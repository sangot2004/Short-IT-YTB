"""Dựng video Shorts bản tin IT (9:16) từ một file kịch bản JSON, rồi gửi qua Telegram.

Lệnh:
  .venv/bin/python ban_tin.py dung  kich-ban/2026-11-25.json [--gui] [--nhap]
  .venv/bin/python ban_tin.py gui   kich-ban/2026-11-25.json
  .venv/bin/python ban_tin.py telegram-id          # lấy chat id sau khi nhắn /start cho bot
  .venv/bin/python ban_tin.py giong                # liệt kê giọng đọc

Xem HUONG-DAN.md để biết cấu trúc file kịch bản.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

GOC = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
SR = 48000

# ---------------------------------------------------------------- cấu hình
CAU_HINH_MAC_DINH = {
    "ten_kenh": "Bản Tin IT",
    "giong": "Minh Đức",
    "nghi_giua_canh": 0.25,
    "toc_do": 1.1,           # tốc độ đọc (1.0 = gốc), giữ nguyên cao độ giọng
    # cách đọc cho các từ viết tắt; chỉ đổi phần ĐỌC, phụ đề vẫn giữ chữ gốc
    "phat_am": {"IT": "ai ti", "DRAM": "đi ram", "TP HCM": "Thành phố Hồ Chí Minh"},
    "nhac_nen": "",          # đường dẫn file nhạc (tùy chọn), phát nhỏ phía sau
    "am_luong_nhac": 0.08,
}


def doc_cau_hinh() -> dict:
    p = GOC / "cau-hinh.json"
    ch = json.loads(json.dumps(CAU_HINH_MAC_DINH))
    if p.exists():
        rieng = json.loads(p.read_text(encoding="utf-8"))
        ch["phat_am"].update(rieng.pop("phat_am", {}))
        ch.update(rieng)
    return ch


def ap_phat_am(text: str, bang: dict) -> str:
    for goc in sorted(bang, key=len, reverse=True):
        text = re.sub(rf"(?<![\wÀ-ỹ]){re.escape(goc)}(?![\wÀ-ỹ])", bang[goc], text)
    return text


def doc_env() -> dict:
    env = {}
    p = GOC / ".env"
    if p.exists():
        for dong in p.read_text(encoding="utf-8").splitlines():
            dong = dong.strip()
            if dong and not dong.startswith("#") and "=" in dong:
                k, v = dong.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ---------------------------------------------------------------- font & màu
HN = "/System/Library/Fonts/HelveticaNeue.ttc"
MONO = "/System/Library/Fonts/SFNSMono.ttf"
_font_cache = {}


def font(co: int, kieu: str = "thuong") -> ImageFont.FreeTypeFont:
    chi_so = {"thuong": 0, "dam": 1, "vua": 10, "hep": 4, "mong": 7}
    k = (co, kieu)
    if k not in _font_cache:
        if kieu == "mono":
            _font_cache[k] = ImageFont.truetype(MONO, co)
        else:
            _font_cache[k] = ImageFont.truetype(HN, co, index=chi_so[kieu])
    return _font_cache[k]


MAU = {
    "nen": (10, 12, 22),
    "the": (20, 24, 41),
    "vien": (44, 50, 82),
    "chu": (236, 238, 245),
    "phu": (150, 156, 180),
    "mo": (98, 104, 130),
    "tim": (139, 124, 255),
    "do": (255, 92, 96),
    "vang": (255, 181, 71),
    "xanh": (61, 220, 151),
    "lam": (80, 170, 255),
    "xam": (154, 160, 180),
}


def mau(ten, mac_dinh="tim"):
    return MAU.get(ten or mac_dinh, MAU[mac_dinh])


def dai(text, f):
    return f.getlength(text)


def xuong_dong(text: str, f, rong: int) -> list[str]:
    dong, hien = [], ""
    for tu in text.split():
        thu = (hien + " " + tu).strip()
        if dai(thu, f) <= rong or not hien:
            hien = thu
        else:
            dong.append(hien)
            hien = tu
    if hien:
        dong.append(hien)
    return dong


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- nền
def ve_nen(ten_kenh: str, nhan: str, giong: str) -> Image.Image:
    img = Image.new("RGBA", (W, H), MAU["nen"] + (255,))
    # quầng sáng tím phía trên
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((W // 2 - 620, -560, W // 2 + 620, 620), fill=(90, 70, 200, 70))
    g.ellipse((-300, 1150, 500, 1900), fill=(40, 90, 200, 28))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    # lưới chấm mờ
    for y in range(40, H, 60):
        for x in range(30, W, 60):
            d.point((x, y), fill=(255, 255, 255, 18))
    # thanh trên: logo + tên kênh + nhãn giọng AI
    d.rounded_rectangle((60, 92, 132, 164), radius=20, fill=MAU["tim"])
    chu_cai = "".join(w[0] for w in ten_kenh.split()[:2]).upper()
    f = font(34, "dam")
    d.text((96, 128), chu_cai, font=f, fill="white", anchor="mm")
    d.text((152, 128), ten_kenh, font=font(38, "dam"), fill=MAU["chu"], anchor="lm")
    d.text((W - 60, 128), f"giọng AI · {giong}", font=font(28, "thuong"), fill=MAU["mo"], anchor="rm")
    # nhãn chương trình
    d.text((W // 2, 262), nhan.upper(), font=font(32, "vua"), fill=MAU["tim"], anchor="mm")
    return img


# ---------------------------------------------------------------- các loại thẻ
# Mỗi hàm trả về (anh_the RGBA, [(anh_muc, (x, y), tre_giay), ...], ham_dong) .
# ham_dong(t) (tùy chọn) trả về ảnh vẽ động theo thời gian, ví dụ số đếm lên.
RONG_THE = 920


def khung_the(cao: int, vien=None) -> Image.Image:
    im = Image.new("RGBA", (RONG_THE, cao), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, RONG_THE - 1, cao - 1), radius=32, fill=MAU["the"] + (245,),
                        outline=(vien or MAU["vien"]) + (255,), width=3)
    return im


def the_tieu_de(c):
    tren, chinh, duoi = c.get("tren", ""), c.get("chinh", ""), c.get("duoi", "")
    fc = font(92, "dam")
    dong = xuong_dong(chinh, fc, RONG_THE - 60)
    cao = 140 + len(dong) * 108 + (90 if duoi else 0)
    im = Image.new("RGBA", (RONG_THE, cao), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 30
    if tren:
        ft = font(36, "vua")
        rw = dai(tren.upper(), ft) + 56
        d.rounded_rectangle(((RONG_THE - rw) / 2, y, (RONG_THE + rw) / 2, y + 64), radius=32,
                            fill=mau(c.get("mau"), "tim") + (255,))
        d.text((RONG_THE / 2, y + 33), tren.upper(), font=ft, fill="white", anchor="mm")
    y = 130
    for s in dong:
        d.text((RONG_THE / 2, y + 50), s, font=fc, fill=MAU["chu"], anchor="mm")
        y += 108
    if duoi:
        d.text((RONG_THE / 2, y + 40), duoi, font=font(40, "thuong"), fill=MAU["phu"], anchor="mm")
    return im, [], None


def the_su_co(c):
    m = mau(c.get("mau"), "do")
    ten, ngay, tt, ct = c.get("ten", ""), c.get("ngay", ""), c.get("trang_thai", ""), c.get("chi_tiet", "")
    fct = font(38, "thuong")
    dong_ct = xuong_dong(ct, fct, RONG_THE - 100) if ct else []
    cao = 330 + len(dong_ct) * 52 + (30 if dong_ct else 0)
    im = khung_the(cao, vien=m)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 40, 10, cao - 40), fill=m + (255,))
    d.text((50, 50), ten, font=font(64, "dam"), fill=MAU["chu"])
    if ngay:
        d.text((50, 138), ngay, font=font(38, "thuong"), fill=MAU["phu"])
    y = 300
    for s in dong_ct:
        d.text((50, y), s, font=fct, fill=MAU["phu"])
        y += 52
    # nhãn trạng thái xuất hiện sau
    nhan = Image.new("RGBA", (RONG_THE - 100, 80), (0, 0, 0, 0))
    dn = ImageDraw.Draw(nhan)
    ft = font(46, "dam")
    rw = dai(tt.upper(), ft) + 110
    dn.rounded_rectangle((0, 0, rw, 76), radius=18, fill=m + (40,), outline=m + (255,), width=3)
    dn.regular_polygon((40, 38, 18), 3, fill=m + (255,)) if c.get("mau", "do") in ("do", "vang") else \
        dn.ellipse((24, 22, 56, 54), fill=m + (255,))
    dn.text((76, 38), tt.upper(), font=ft, fill=m, anchor="lm")
    return im, [(nhan, (50, 200), 0.45)], None


def the_bang(c):
    tieu_de, cot, dong, ghi_chu = c.get("tieu_de", ""), c.get("cot", []), c.get("dong", []), c.get("ghi_chu", "")
    hang = 92
    cao = (110 if tieu_de else 30) + (70 if cot else 0) + len(dong) * hang + (120 if ghi_chu else 30)
    im = khung_the(cao)
    d = ImageDraw.Draw(im)
    y = 30
    if tieu_de:
        d.text((50, y + 10), tieu_de, font=font(46, "dam"), fill=MAU["vang"])
        y += 110
    if cot:
        fh = font(30, "vua")
        d.text((50, y), cot[0].upper(), font=fh, fill=MAU["mo"])
        if len(cot) > 1:
            d.text((RONG_THE - 50, y), cot[1].upper(), font=fh, fill=MAU["mo"], anchor="ra")
        y += 70
    muc = []
    for i, r in enumerate(dong):
        trai, phai = r[0], r[1] if len(r) > 1 else ""
        m = mau(r[2] if len(r) > 2 else None, "chu") if len(r) > 2 else MAU["chu"]
        a = Image.new("RGBA", (RONG_THE - 60, hang), (0, 0, 0, 0))
        da = ImageDraw.Draw(a)
        da.line((20, 0, RONG_THE - 80, 0), fill=MAU["vien"] + (255,), width=2)
        da.text((20, hang / 2), trai, font=font(44, "vua"), fill=MAU["chu"], anchor="lm")
        da.text((RONG_THE - 80, hang / 2), phai.upper(), font=font(42, "dam"), fill=m, anchor="rm")
        muc.append((a, (30, y), 0.3 + i * 0.28))
        y += hang
    if ghi_chu:
        d.text((50, y + 30), ghi_chu, font=font(32, "thuong"), fill=MAU["mo"])
    return im, muc, None


def the_so_lon(c):
    so, nhan_, phu = str(c.get("so", "")), c.get("nhan", ""), c.get("phu", "")
    m = mau(c.get("mau"), "xanh")
    fn = font(44, "vua")
    dong_nhan = xuong_dong(nhan_, fn, RONG_THE - 100)
    cao = 330 + len(dong_nhan) * 60 + (70 if phu else 0)
    im = khung_the(cao)
    d = ImageDraw.Draw(im)
    y = 280
    for s in dong_nhan:
        d.text((RONG_THE / 2, y), s, font=fn, fill=MAU["chu"], anchor="mm")
        y += 60
    if phu:
        d.text((RONG_THE / 2, y + 10), phu, font=font(34, "thuong"), fill=MAU["phu"], anchor="mm")

    khop = re.match(r"^([^\d]*)([\d.,]+)(.*)$", so)
    fs = font(190, "dam")
    cache = {}

    def dong(t):
        if khop:
            dau, so_chu, duoi = khop.groups()
            gia_tri = float(so_chu.replace(".", "").replace(",", "."))
            co_thap_phan = "," in so_chu
            v = gia_tri * ease(t / 1.1)
            s = f"{v:.1f}".replace(".", ",") if co_thap_phan else f"{int(round(v)):,}".replace(",", ".")
            text = dau + s + duoi
        else:
            text = so
        if text not in cache:
            a = Image.new("RGBA", (RONG_THE, 230), (0, 0, 0, 0))
            ImageDraw.Draw(a).text((RONG_THE / 2, 115), text, font=fs, fill=m, anchor="mm")
            cache[text] = a
        return cache[text], (0, 40)

    return im, [], dong


def the_tin(c):
    nguon, tieu_de, y_chinh = c.get("nguon", ""), c.get("tieu_de", ""), c.get("y", [])
    ft = font(56, "dam")
    fy = font(42, "thuong")
    dong_td = xuong_dong(tieu_de, ft, RONG_THE - 100)
    dong_y = [xuong_dong(s, fy, RONG_THE - 150) for s in y_chinh]
    cao = 120 + len(dong_td) * 68 + 30 + sum(len(x) * 56 + 26 for x in dong_y) + 30
    im = khung_the(cao)
    d = ImageDraw.Draw(im)
    if nguon:
        d.text((50, 46), nguon.upper(), font=font(30, "vua"), fill=MAU["tim"])
    y = 110
    for s in dong_td:
        d.text((50, y), s, font=ft, fill=MAU["chu"])
        y += 68
    y += 30
    muc = []
    for i, ds in enumerate(dong_y):
        a = Image.new("RGBA", (RONG_THE - 60, len(ds) * 56 + 10), (0, 0, 0, 0))
        da = ImageDraw.Draw(a)
        da.ellipse((22, 18, 40, 36), fill=MAU["xanh"])
        for j, s in enumerate(ds):
            da.text((70, j * 56), s, font=fy, fill=MAU["phu"])
        muc.append((a, (30, y), 0.4 + i * 0.6))
        y += len(ds) * 56 + 26
    return im, muc, None


def the_ket(c):
    chinh, phu = c.get("chinh", "Follow để cập nhật tin IT mỗi ngày"), c.get("phu", "")
    fc = font(70, "dam")
    dong = xuong_dong(chinh, fc, RONG_THE - 80)
    cao = 200 + len(dong) * 86 + (70 if phu else 0)
    im = Image.new("RGBA", (RONG_THE, cao), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y = 20
    for s in dong:
        d.text((RONG_THE / 2, y + 40), s, font=fc, fill=MAU["chu"], anchor="mm")
        y += 86
    if phu:
        d.text((RONG_THE / 2, y + 30), phu, font=font(40, "thuong"), fill=MAU["phu"], anchor="mm")
        y += 70
    nut = Image.new("RGBA", (RONG_THE, 120), (0, 0, 0, 0))
    dn = ImageDraw.Draw(nut)
    dn.rounded_rectangle((RONG_THE / 2 - 210, 10, RONG_THE / 2 + 210, 110), radius=50, fill=MAU["do"])
    dn.text((RONG_THE / 2, 60), "FOLLOW", font=font(52, "dam"), fill="white", anchor="mm")
    return im, [(nut, (0, y + 30), 0.5)], None


def the_code(c):
    tieu_de, code = c.get("tieu_de", ""), c.get("code", "")
    fm = font(36, "mono")
    dong = code.split("\n")
    cao = (110 if tieu_de else 40) + len(dong) * 52 + 50
    im = khung_the(cao)
    d = ImageDraw.Draw(im)
    if tieu_de:
        d.text((50, 40), tieu_de, font=font(40, "dam"), fill=MAU["vang"])
    y = 110 if tieu_de else 40
    for s in dong:
        mau_dong = MAU["mo"] if s.strip().startswith(("--", "#")) else MAU["chu"]
        d.text((50, y), s, font=fm, fill=mau_dong)
        y += 52
    return im, [], None


LOAI_THE = {
    "tieu_de": the_tieu_de, "su_co": the_su_co, "bang": the_bang, "so_lon": the_so_lon,
    "tin": the_tin, "ket": the_ket, "code": the_code,
}


# ---------------------------------------------------------------- phụ đề
def chia_phu_de(text: str, toi_da_tu: int = 8) -> list[str]:
    cau = [s.strip() for s in re.split(r"(?<=[.,!?;:…])\s+", text) if s.strip()]
    kq = []
    for c in cau:
        tu = c.split()
        so_phan = math.ceil(len(tu) / toi_da_tu)
        co = math.ceil(len(tu) / so_phan)
        for i in range(0, len(tu), co):
            kq.append(" ".join(tu[i:i + co]))
    # gộp mẩu quá ngắn (ví dụ "Ba.") vào mẩu sau
    gop = []
    for p in kq:
        if gop and len(gop[-1].split()) < 3 and len(gop[-1].split()) + len(p.split()) <= toi_da_tu + 2:
            gop[-1] = gop[-1] + " " + p
        else:
            gop.append(p)
    return gop


def ve_phu_de(text: str) -> Image.Image:
    f = font(64, "dam")
    dong = xuong_dong(text, f, 940)
    im = Image.new("RGBA", (W, len(dong) * 84 + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, s in enumerate(dong):
        d.text((W / 2, 15 + i * 84 + 40), s, font=f, fill=MAU["chu"], anchor="mm",
               stroke_width=6, stroke_fill=(5, 6, 12))
    return im


# ---------------------------------------------------------------- giọng đọc
_tts = None


def tao_giong(text: str, giong: str, thu_muc: Path, toc_do: float = 1.0) -> Path:
    goc = _tao_giong_goc(text, giong, thu_muc)
    if abs(toc_do - 1.0) < 0.01:
        return goc
    p = goc.with_name(f"{goc.stem}-x{toc_do:.2f}.wav")
    if not p.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(goc), "-filter:a", f"atempo={toc_do}",
                        str(p)], check=True)
    return p


def _tao_giong_goc(text: str, giong: str, thu_muc: Path) -> Path:
    global _tts
    khoa = hashlib.sha1(f"{giong}|{text}".encode()).hexdigest()[:16]
    p = thu_muc / f"{khoa}.wav"
    if p.exists():
        return p
    if _tts is None:
        print("  · nạp mô hình giọng VieNeu (lần đầu ~40 giây)…")
        from vieneu import Vieneu
        _tts = Vieneu()
    a = _tts.infer(text, voice=giong)
    _tts.save(a, str(p))
    return p


def doc_wav(p: Path) -> np.ndarray:
    a, sr = sf.read(str(p), dtype="float32", always_2d=False)
    if a.ndim > 1:
        a = a.mean(axis=1)
    if sr != SR:
        x = np.linspace(0, len(a), int(len(a) * SR / sr), endpoint=False)
        a = np.interp(x, np.arange(len(a)), a).astype("float32")
    # cắt bớt khoảng lặng đầu/cuối
    nguong = 0.01
    idx = np.where(np.abs(a) > nguong)[0]
    if len(idx):
        a = a[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.08 * SR)]
    return a


# ---------------------------------------------------------------- dựng
def dung(duong_dan_kb: Path, nhap: bool = False) -> Path:
    t0 = time.time()
    kb = json.loads(duong_dan_kb.read_text(encoding="utf-8"))
    ch = doc_cau_hinh()
    giong = kb.get("giong") or ch["giong"]
    ten = duong_dan_kb.stem
    cache = GOC / "tam" / "giong"
    cache.mkdir(parents=True, exist_ok=True)
    xuat = GOC / "xuat"
    xuat.mkdir(exist_ok=True)

    # 1. giọng đọc từng cảnh
    print(f"[1/3] Tạo giọng đọc ({giong})…")
    nghi = np.zeros(int(ch["nghi_giua_canh"] * SR), dtype="float32")
    am, canh = [], []
    t = 0.0
    for i, c in enumerate(kb["canh"]):
        a = doc_wav(tao_giong(c.get("doc") or ap_phat_am(c["loi"], ch["phat_am"]), giong, cache, ch["toc_do"]))
        dur = len(a) / SR + ch["nghi_giua_canh"]
        canh.append({"bat_dau": t, "dai": dur, "noi": len(a) / SR, **c})
        am += [a, nghi]
        t += dur
        print(f"  cảnh {i + 1}: {dur:.1f}s")
    tong = t + 0.3
    am.append(np.zeros(int(0.3 * SR), dtype="float32"))
    wav = GOC / "tam" / f"{ten}.wav"
    sf.write(str(wav), np.concatenate(am), SR)
    print(f"  tổng: {tong:.1f}s")

    # 2. chuẩn bị hình
    print("[2/3] Vẽ thẻ và phụ đề…")
    nen = ve_nen(ch["ten_kenh"], kb.get("nhan", "Bản tin IT"), giong)
    for c in canh:
        the = c.get("the") or {"loai": "tieu_de", "chinh": ""}
        im, muc, ham_dong = LOAI_THE[the["loai"]](the)
        c["_the"], c["_muc"], c["_dong"] = im, muc, ham_dong
        c["_vi_tri"] = ((W - RONG_THE) // 2, max(330, 790 - im.height // 2))
        # phụ đề: chia theo độ dài chữ
        phan = chia_phu_de(c["loi"])
        trong_so = [len(p) + 6 for p in phan]
        s = sum(trong_so)
        tt = 0.0
        c["_pd"] = []
        for p, w in zip(phan, trong_so):
            d = c["noi"] * w / s
            c["_pd"].append((tt, tt + d, ve_phu_de(p)))
            tt += d

    # 3. xuất từng khung hình qua ffmpeg
    print("[3/3] Xuất video…")
    ra = xuat / f"{ten}{'-nhap' if nhap else ''}.mp4"
    fps = 15 if nhap else FPS
    lenh = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(wav)]
    if ch.get("nhac_nen") and Path(ch["nhac_nen"]).exists():
        lenh += ["-stream_loop", "-1", "-i", ch["nhac_nen"], "-filter_complex",
                 f"[2:a]volume={ch['am_luong_nhac']}[n];[1:a][n]amix=inputs=2:duration=first[a]",
                 "-map", "0:v", "-map", "[a]"]
    else:
        lenh += ["-map", "0:v", "-map", "1:a"]
    lenh += ["-c:v", "libx264", "-preset", "veryfast" if nhap else "medium", "-crf", "28" if nhap else "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(ra)]
    ff = subprocess.Popen(lenh, stdin=subprocess.PIPE)

    tinh = {}  # cache khung tĩnh theo trạng thái
    so_khung = int(tong * fps)
    ci = 0
    for k in range(so_khung):
        t = k / fps
        while ci < len(canh) - 1 and t >= canh[ci + 1]["bat_dau"]:
            ci += 1
        c = canh[ci]
        lt = t - c["bat_dau"]
        a_the = round(ease(lt / 0.4) * 20) / 20
        a_muc = tuple(round(ease((lt - tre) / 0.35) * 20) / 20 for _, _, tre in c["_muc"])
        dong_img = c["_dong"](lt) if c["_dong"] else None
        khoa = (ci, a_the, a_muc, id(dong_img[0]) if dong_img else 0)
        if khoa not in tinh:
            if len(tinh) > 400:
                tinh.clear()
            khung = nen.copy()
            lop = Image.new("RGBA", (RONG_THE, c["_the"].height + 400), (0, 0, 0, 0))
            lop.alpha_composite(c["_the"])
            for (img, (x, y), _), a in zip(c["_muc"], a_muc):
                if a > 0:
                    m = img if a >= 1 else Image.fromarray(
                        (np.asarray(img) * np.array([1, 1, 1, a])).astype("uint8"), "RGBA")
                    lop.alpha_composite(m, (int(x), int(y + (1 - a) * 20)))
            if dong_img:
                lop.alpha_composite(dong_img[0], dong_img[1])
            if a_the < 1:
                lop = Image.fromarray((np.asarray(lop) * np.array([1, 1, 1, a_the])).astype("uint8"), "RGBA")
            vx, vy = c["_vi_tri"]
            khung.alpha_composite(lop, (vx, int(vy + (1 - a_the) * 60)))
            tinh[khoa] = khung
        khung = tinh[khoa].copy()
        # phụ đề
        for bd, kt, img in c["_pd"]:
            if bd <= lt < kt + 0.05:
                khung.alpha_composite(img, (0, 1330))
                break
        # thanh tiến trình
        d = ImageDraw.Draw(khung)
        d.rectangle((0, 0, int(W * t / tong), 8), fill=MAU["tim"])
        ff.stdin.write(khung.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    if ff.returncode:
        sys.exit("ffmpeg lỗi")

    # gói đăng bài
    dang = kb.get("dang", {})
    txt = f"{dang.get('tieu_de', '')}\n\n{dang.get('mo_ta', '')}\n\n{' '.join(dang.get('hashtag', []))}\n"
    (xuat / f"{ten}-dang.txt").write_text(txt, encoding="utf-8")
    mb = ra.stat().st_size / 1e6
    print(f"Xong: {ra} ({tong:.1f}s, {mb:.1f} MB) trong {time.time() - t0:.0f}s")
    return ra


# ---------------------------------------------------------------- telegram
def telegram(phuong_thuc: str, **kw):
    import requests
    env = doc_env()
    token = env.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Thiếu TELEGRAM_BOT_TOKEN trong file .env (xem HUONG-DAN.md)")
    r = requests.post(f"https://api.telegram.org/bot{token}/{phuong_thuc}", timeout=300, **kw)
    j = r.json()
    if not j.get("ok"):
        sys.exit(f"Telegram lỗi: {j.get('description')}")
    return j["result"]


def gui(duong_dan_kb: Path):
    env = doc_env()
    chat = env.get("TELEGRAM_CHAT_ID")
    if not chat:
        sys.exit("Thiếu TELEGRAM_CHAT_ID trong .env — chạy: ban_tin.py telegram-id")
    kb = json.loads(duong_dan_kb.read_text(encoding="utf-8"))
    ten = duong_dan_kb.stem
    video = GOC / "xuat" / f"{ten}.mp4"
    if not video.exists():
        sys.exit(f"Chưa có video {video} — chạy lệnh dung trước")
    if video.stat().st_size > 49e6:
        sys.exit("Video lớn hơn 50 MB, bot Telegram không gửi được")
    dang = kb.get("dang", {})
    with open(video, "rb") as f:
        telegram("sendVideo", data={"chat_id": chat, "caption": f"🎬 {dang.get('tieu_de', ten)}",
                                    "supports_streaming": "true", "width": W, "height": H},
                 files={"video": (video.name, f, "video/mp4")})
    nguon = "\n".join(f"• {x}" for x in kb.get("nguon", []))
    telegram("sendMessage", data={"chat_id": chat, "text":
             f"TIÊU ĐỀ:\n{dang.get('tieu_de', '')}\n\nMÔ TẢ:\n{dang.get('mo_ta', '')}\n\n"
             f"{' '.join(dang.get('hashtag', []))}" + (f"\n\nNGUỒN (kiểm tra trước khi đăng):\n{nguon}" if nguon else ""),
             "disable_web_page_preview": "true"})
    print("Đã gửi video và nội dung đăng bài qua Telegram")


def telegram_id():
    kq = telegram("getUpdates")
    if not kq:
        print("Chưa thấy tin nhắn nào. Mở bot trên Telegram, bấm Start (hoặc gửi /start), rồi chạy lại.")
        return
    da = set()
    for u in kq:
        m = u.get("message") or u.get("channel_post") or {}
        c = m.get("chat", {})
        if c.get("id") and c["id"] not in da:
            da.add(c["id"])
            print(f"chat id: {c['id']}  ({c.get('first_name') or c.get('title', '')})")
    print("Dán số chat id vào .env: TELEGRAM_CHAT_ID=...")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="lenh", required=True)
    p = sp.add_parser("dung")
    p.add_argument("kich_ban", type=Path)
    p.add_argument("--gui", action="store_true", help="gửi qua Telegram sau khi dựng")
    p.add_argument("--nhap", action="store_true", help="bản nháp 15 fps cho nhanh")
    p = sp.add_parser("gui")
    p.add_argument("kich_ban", type=Path)
    sp.add_parser("telegram-id")
    sp.add_parser("giong")
    a = ap.parse_args()
    if a.lenh == "dung":
        dung(a.kich_ban, a.nhap)
        if a.gui and not a.nhap:
            gui(a.kich_ban)
    elif a.lenh == "gui":
        gui(a.kich_ban)
    elif a.lenh == "telegram-id":
        telegram_id()
    elif a.lenh == "giong":
        from vieneu import Vieneu
        for mo_ta, _ in Vieneu().list_preset_voices():
            print(mo_ta)


if __name__ == "__main__":
    main()
