#!/usr/bin/env python3
"""Công cụ dựng video tự động cho kênh YouTube.

Các lệnh:
  tao        Tạo dự án mới từ file kịch bản (.md)
  trang-thai Xem cảnh nào đã có ảnh, cảnh nào còn thiếu
  phu-de     Nghe giọng đọc, khớp với kịch bản, xuất phụ đề .srt
  dung       Dựng video hoàn chỉnh (thêm --nhap để dựng bản xem nhanh)

Xem hướng dẫn đầy đủ trong cong-cu/HUONG-DAN.md
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from fnmatch import fnmatch
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
VID_EXT = {".mp4", ".mov", ".m4v", ".webm"}
AUD_EXT = {".mp3", ".wav", ".m4a", ".aac", ".aiff", ".aif", ".flac", ".ogg"}
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
EFFECTS = ["vao", "phai", "ra", "trai"]
FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
TAIL = 2.0          # giây thêm vào sau câu cuối
LEAD = 0.25         # đổi ảnh sớm hơn lời đọc một chút cho tự nhiên
GAP_GIUA_FILE = 0.7  # giây nghỉ chèn giữa các file giọng (chỉnh bằng nghi_giua_cac_file trong phan-canh.yaml)
LONG_IMAGE = 12.0   # ảnh hiển thị lâu hơn số giây này sẽ bị cảnh báo
# Cắt viền phải/dưới để loại dấu ngôi sao nhỏ của Gemini (tắt bằng cat_dau_sao: false trong phan-canh.yaml)
WATERMARK_CROP = "crop=iw*0.96:ih*0.945:0:0,"

YAML_HEADER = """\
# BẢNG PHÂN CẢNH
# - Mỗi cảnh ứng với một dòng [HÌNH: ...] trong kịch bản.
# - "anh": danh sách tên file trong thư mục anh/ (dùng được dấu * ).
#   Mặc định cảnh 1 lấy mọi file bắt đầu bằng "canh-01", ví dụ:
#     canh-01.png, canh-01b.png, canh-01-a1.jpg, canh-01-chuyen-dong.mp4
#   Các file được chia đều thời gian của cảnh, theo thứ tự tên file.
# - "hieu_ung" (tuỳ chọn): vao | ra | trai | phai | tinh
# - "loi": lời đọc của cảnh. Nếu bạn sửa lời khi thu âm, sửa ở đây cho khớp
#   để phụ đề đúng chính tả.
"""


# ----------------------------------------------------------------- tiện ích
def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"\n❌ Lỗi khi chạy lệnh:\n{' '.join(map(str, cmd))}\n{r.stderr[-2000:]}")
    return r


def need_ffmpeg():
    if not shutil.which("ffmpeg"):
        sys.exit("❌ Chưa cài ffmpeg. Chạy: brew install ffmpeg")


def clip_len(path):
    return audio_len(path)


def audio_len(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(path)])
    return float(r.stdout.strip())


def norm(word):
    w = unicodedata.normalize("NFD", word.replace("đ", "d").replace("Đ", "d"))
    w = "".join(c for c in w if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]", "", w)


def clean_md(s):
    s = re.sub(r"^>\s*", "", s)
    s = s.replace("**", "").replace("__", "")
    s = re.sub(r"(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)", "", s)
    return s.strip()


def fmt_time(t):
    t = max(t, 0)
    h, rem = divmod(int(t * 1000), 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def file_sig(paths):
    h = hashlib.sha1()
    for p in paths:
        st = p.stat()
        h.update(f"{p.name}|{st.st_size}|{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(str, lambda d, s: d.represent_scalar(
    "tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


# ----------------------------------------------------------------- dự án
def resolve_project(arg):
    p = Path(arg).expanduser()
    if not p.is_absolute() and not p.exists():
        p = ROOT / "du-an" / arg
    return p.resolve()


def load_project(proj):
    f = proj / "phan-canh.yaml"
    if not f.exists():
        sys.exit(f"❌ Không thấy {f}. Hãy tạo dự án trước bằng lệnh: tao")
    data = yaml.safe_load(f.read_text(encoding="utf-8"))
    for i, sc in enumerate(data["canh"]):
        sc.setdefault("so", i + 1)
        sc.setdefault("anh", [f"canh-{sc['so']:02d}*"])
        sc["loi"] = (sc.get("loi") or "").strip()
    return data


def parse_script(text):
    text = unicodedata.normalize("NFC", text)
    scenes, started = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if "GÓI ĐĂNG VIDEO" in line:
            break
        if re.match(r"^##\s+\d", line):
            started = True
            continue
        if not started or not line or line.startswith("---") or line.startswith("#"):
            continue
        m = re.match(r"^\[HÌNH:\s*(.*?)\]\s*$", line)
        if m:
            scenes.append({"mo_ta": m.group(1), "loi": []})
            continue
        if line.startswith("["):
            continue
        t = clean_md(line)
        if not t:
            continue
        if not scenes:
            scenes.append({"mo_ta": "(mở đầu)", "loi": []})
        scenes[-1]["loi"].append(t)
    return scenes


def cmd_tao(args):
    script = Path(args.kich_ban).expanduser().resolve()
    if not script.exists():
        sys.exit(f"❌ Không thấy file kịch bản: {script}")
    proj = Path(args.du_an).expanduser() if "/" in args.du_an else ROOT / "du-an" / args.du_an
    proj = proj.resolve()
    yml = proj / "phan-canh.yaml"
    if yml.exists() and not args.ghi_de:
        sys.exit(f"❌ Dự án đã có {yml}. Thêm --ghi-de nếu muốn tạo lại (sẽ mất chỉnh sửa cũ).")
    scenes = parse_script(script.read_text(encoding="utf-8"))
    if not scenes:
        sys.exit("❌ Không tìm thấy dòng [HÌNH: ...] nào trong kịch bản.")
    for d in ("anh", "giong", "nhac", "xuat"):
        (proj / d).mkdir(parents=True, exist_ok=True)
    data = {"du_an": proj.name, "kich_ban": str(script), "am_luong_nhac": 0.15, "canh": []}
    for i, sc in enumerate(scenes, 1):
        data["canh"].append({"so": i, "mo_ta": sc["mo_ta"], "anh": [f"canh-{i:02d}*"],
                             "loi": "\n".join(sc["loi"])})
    yml.write_text(YAML_HEADER + yaml.dump(data, Dumper=Dumper, allow_unicode=True,
                                           sort_keys=False, width=1000), encoding="utf-8")
    loi = "\n\n".join(f"[Cảnh {i}]\n" + "\n".join(sc["loi"]) for i, sc in enumerate(scenes, 1))
    (proj / "loi-doc.txt").write_text(loi + "\n", encoding="utf-8")
    print(f"✅ Đã tạo dự án: {proj}")
    print(f"   {len(scenes)} cảnh, {sum(len(' '.join(s['loi']).split()) for s in scenes)} chữ lời đọc")
    print("   Việc tiếp theo:")
    print("   1. Bỏ ảnh vào anh/ theo tên canh-01.png, canh-02.png, ...")
    print("   2. Bỏ file giọng đọc vào giong/  (đọc theo loi-doc.txt)")
    print("   3. (Tuỳ chọn) Bỏ 1 file nhạc nền vào nhac/")


# ----------------------------------------------------------------- media
def media_for(proj, scene):
    files = sorted(p for p in (proj / "anh").iterdir()
                   if p.suffix.lower() in IMG_EXT | VID_EXT) if (proj / "anh").exists() else []
    out = []
    for pat in scene["anh"]:
        for p in files:
            if fnmatch(p.name, pat) and p not in out:
                out.append(p)
    return out


def voice_files(proj):
    d = proj / "giong"
    return sorted(p for p in d.iterdir() if p.suffix.lower() in AUD_EXT) if d.exists() else []


def music_file(proj):
    d = proj / "nhac"
    fs = sorted(p for p in d.iterdir() if p.suffix.lower() in AUD_EXT) if d.exists() else []
    return fs[0] if fs else None


def cmd_trang_thai(args):
    proj = resolve_project(args.du_an)
    data = load_project(proj)
    missing = 0
    print(f"📁 {proj}\n")
    for sc in data["canh"]:
        ms = media_for(proj, sc)
        mark = "✅" if ms else "⬜"
        missing += not ms
        names = ", ".join(m.name for m in ms) if ms else "(chưa có ảnh)"
        print(f"{mark} Cảnh {sc['so']:>2}: {names}")
        print(f"      {sc['mo_ta'][:90]}")
    vs = voice_files(proj)
    mu = music_file(proj)
    print()
    print(f"🎙  Giọng đọc: {', '.join(v.name for v in vs) if vs else 'chưa có'}")
    print(f"🎵 Nhạc nền:  {mu.name if mu else 'chưa có (không bắt buộc)'}")
    print(f"\nCòn thiếu ảnh: {missing}/{len(data['canh'])} cảnh"
          + (" (khi dựng, cảnh thiếu sẽ hiện khung ghi chú)" if missing else ""))


# ----------------------------------------------------------------- giọng đọc & phụ đề
def ensure_transcript(proj, data):
    vs = voice_files(proj)
    if not vs:
        sys.exit("❌ Chưa có file giọng đọc trong giong/")
    build = proj / "build"
    build.mkdir(exist_ok=True)
    gap = float(data.get("nghi_giua_cac_file", GAP_GIUA_FILE))
    sig = file_sig(vs) + f"-g{gap}"
    wav = build / "giong-tong.wav"
    tj = build / "transcript.json"
    if tj.exists():
        old = json.loads(tj.read_text(encoding="utf-8"))
        if old.get("sig") == sig and wav.exists():
            return old, wav
    print(f"🎙  Ghép {len(vs)} file giọng đọc...")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for v in vs:
        cmd += ["-i", str(v)]
    fc = "".join(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo"
                 + (f",apad=pad_dur={gap}" if i < len(vs) - 1 and gap > 0 else "")
                 + f"[a{i}];" for i in range(len(vs)))
    fc += "".join(f"[a{i}]" for i in range(len(vs))) + f"concat=n={len(vs)}:v=0:a=1[out]"
    run(cmd + ["-filter_complex", fc, "-map", "[out]", "-c:a", "pcm_s16le", str(wav)])

    print("🧠 Đang nghe giọng đọc bằng Whisper (lần đầu sẽ tải mô hình khoảng 1,6 GB)...")
    import mlx_whisper
    t0 = time.time()
    res = mlx_whisper.transcribe(str(wav), path_or_hf_repo=WHISPER_MODEL, language="vi",
                                 word_timestamps=True, initial_prompt=name_prompt(data),
                                 condition_on_previous_text=False, verbose=False)
    words = [{"w": w["word"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3)}
             for seg in res["segments"] for w in seg.get("words", []) if w["word"].strip()]
    out = {"sig": sig, "duration": audio_len(wav), "words": words}
    tj.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"   Xong sau {time.time() - t0:.0f} giây, nhận được {len(words)} chữ.")
    return out, wav


def name_prompt(data):
    text = " ".join(sc["loi"] for sc in data["canh"])
    names, seq = [], []
    for tok in text.split() + [""]:
        t = re.sub(r"[^\wÀ-ỹ]", "", tok)
        if t and t[0].isupper():
            seq.append(t)
            continue
        if len(seq) >= 2:
            n = " ".join(seq)
            if n not in names:
                names.append(n)
        seq = []
    return ", ".join(names[:40]) + "." if names else None


def align(data, tr):
    """Gán thời gian cho từng chữ trong kịch bản dựa trên lời Whisper nghe được."""
    words, scene_start = [], []
    for sc in data["canh"]:
        scene_start.append(len(words))
        words += sc["loi"].split()
    hyp = [w for w in tr["words"] if norm(w["w"])]
    a = [norm(w) for w in words]
    b = [norm(w["w"]) for w in hyp]
    times = [None] * len(words)
    matched = 0
    for blk in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            h = hyp[blk.b + k]
            times[blk.a + k] = (h["s"], h["e"])
            matched += 1
    dur = tr["duration"]
    # nội suy cho các chữ không khớp
    i = 0
    while i < len(words):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(words) and times[j] is None:
            j += 1
        t0 = times[i - 1][1] if i > 0 else 0.0
        t1 = times[j][0] if j < len(words) else dur
        step = max(t1 - t0, 0) / (j - i)
        for k in range(i, j):
            times[k] = (t0 + step * (k - i), t0 + step * (k - i + 1))
        i = j
    ratio = matched / max(len(words), 1)
    return words, times, scene_start, ratio


MAX_CUE = 45  # số ký tự tối đa mỗi dòng phụ đề


def _text(words, idx):
    return " ".join(words[k] for k in idx)


def _split_even(words, idx):
    """Chia một cụm chữ quá dài thành các phần dài gần bằng nhau."""
    n = -(-len(_text(words, idx)) // MAX_CUE)
    size = -(-len(idx) // n)
    return [idx[k:k + size] for k in range(0, len(idx), size)]


def make_cues(words, times):
    # 1) tách câu theo dấu chấm câu hoặc khoảng lặng dài
    sentences, cur = [], []
    for i, w in enumerate(words):
        if cur and times[i][0] - times[cur[-1]][1] > 0.8:
            sentences.append(cur)
            cur = []
        cur.append(i)
        if re.search(r"[.?!…:]['\"”’)]*$", w):
            sentences.append(cur)
            cur = []
    if cur:
        sentences.append(cur)
    # 2) câu dài thì tách theo dấu phẩy, rồi gom lại cho vừa một dòng
    cues = []
    for s in sentences:
        if len(_text(words, s)) <= MAX_CUE:
            cues.append(s)
            continue
        clauses, cl = [], []
        for i in s:
            cl.append(i)
            if re.search(r"[,;–—]['\"”’)]*$", words[i]):
                clauses.append(cl)
                cl = []
        if cl:
            clauses.append(cl)
        pack = []
        for cl in clauses:
            if pack and len(_text(words, pack + cl)) > MAX_CUE:
                cues += _split_even(words, pack) if len(_text(words, pack)) > MAX_CUE else [pack]
                pack = []
            pack = pack + cl
        if pack:
            cues += _split_even(words, pack) if len(_text(words, pack)) > MAX_CUE else [pack]
    return cues


def write_srt(words, times, path):
    cues = make_cues(words, times)
    lines = []
    prev_end = 0.0
    for n, c in enumerate(cues, 1):
        s = max(times[c[0]][0], prev_end)
        e = max(times[c[-1]][1], s + 0.8)
        if n < len(cues):
            e = min(e, times[cues[n][0]][0]) if times[cues[n][0]][0] > s else e
        prev_end = e
        lines.append(f"{n}\n{fmt_time(s)} --> {fmt_time(e)}\n{' '.join(words[k] for k in c)}\n")
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(cues)


def scene_times(data, times, scene_start, total):
    n = len(data["canh"])
    starts = []
    for k in range(n):
        idx = scene_start[k]
        if k == 0:
            starts.append(0.0)
        elif idx < len(times):
            starts.append(max(times[idx][0] - LEAD, starts[-1]))
        else:
            starts.append(total)
    # các cảnh liền nhau không có lời đọc: chia đều thời gian
    k = 0
    while k < n:
        j = k
        while j + 1 < n and abs(starts[j + 1] - starts[k]) < 0.01:
            j += 1
        end = starts[j + 1] if j + 1 < n else total
        if j > k:
            step = (end - starts[k]) / (j - k + 1)
            for m in range(k, j + 1):
                starts[m] = starts[k] + step * (m - k)
        k = j + 1
    ends = starts[1:] + [total]
    return list(zip(starts, ends))


def cmd_phu_de(args):
    need_ffmpeg()
    proj = resolve_project(args.du_an)
    data = load_project(proj)
    tr, _ = ensure_transcript(proj, data)
    words, times, scene_start, ratio = align(data, tr)
    srt = proj / "xuat" / "phu-de.srt"
    srt.parent.mkdir(exist_ok=True)
    n = write_srt(words, times, srt)
    print(f"✅ Phụ đề: {srt}  ({n} dòng)")
    report_match(ratio)


def report_match(ratio):
    print(f"   Độ khớp giữa giọng đọc và kịch bản: {ratio:.0%}")
    if ratio < 0.6:
        print("   ⚠️  Khớp thấp: có thể bạn đọc khác kịch bản nhiều, hoặc file giọng sai."
              " Hãy sửa phần 'loi' trong phan-canh.yaml cho đúng lời đã đọc.")


# ----------------------------------------------------------------- dựng hình
def placeholder(proj, scene, size):
    from PIL import Image, ImageDraw, ImageFont
    out = proj / "build" / "cho-trong" / f"canh-{scene['so']:02d}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H = size
    img = Image.new("RGB", (W, H), (28, 30, 34))
    d = ImageDraw.Draw(img)
    try:
        big = ImageFont.truetype(FONT, H // 14)
        small = ImageFont.truetype(FONT, H // 30)
    except OSError:
        big = small = ImageFont.load_default()
    d.text((W * 0.06, H * 0.30), f"THIẾU ẢNH · CẢNH {scene['so']}", font=big, fill=(230, 180, 90))
    desc, line, y = scene["mo_ta"].split(), "", H * 0.48
    for w in desc:
        if d.textlength(line + " " + w, font=small) > W * 0.86:
            d.text((W * 0.06, y), line.strip(), font=small, fill=(200, 200, 200))
            y += H / 22
            line = ""
        line += " " + w
    d.text((W * 0.06, y), line.strip(), font=small, fill=(200, 200, 200))
    img.save(out)
    return out


def zoom_expr(effect, frames):
    p = f"(on/{max(frames - 1, 1)})"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    return {
        "vao": (f"1+0.15*{p}", cx, cy),
        "ra": (f"1.15-0.15*{p}", cx, cy),
        "phai": ("1.12", f"(iw-iw/zoom)*{p}", cy),
        "trai": ("1.12", f"(iw-iw/zoom)*(1-{p})", cy),
        "tinh": ("1", "0", "0"),
    }[effect]


def render_segment(seg, q):
    W, H = q["size"]
    frames = seg["frames"]
    fades = []
    if seg.get("fade_in"):
        fades.append("fade=t=in:st=0:d=0.8")
    if seg.get("fade_out"):
        fades.append(f"fade=t=out:st={max(frames / FPS - 1.5, 0):.2f}:d=1.5")
    tail = ",".join(fades + ["format=yuv420p"])
    src = seg["src"]
    pre = WATERMARK_CROP if q.get("cat") else ""
    if src.suffix.lower() in VID_EXT:
        vf = (f"{pre}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
              f"fps={FPS},tpad=stop_mode=clone:stop_duration={frames / FPS + 1:.2f},{tail}")
        inp = ["-i", str(src)]
    else:
        z, x, y = zoom_expr(seg["effect"], frames)
        PW, PH = W * 2, H * 2
        vf = (f"{pre}scale={PW}:{PH}:force_original_aspect_ratio=increase,crop={PW}:{PH},setsar=1,"
              f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},{tail}")
        inp = ["-i", str(src)]
    run(["ffmpeg", "-y", "-loglevel", "error", *inp, "-vf", vf, "-an", "-frames:v", str(frames),
         "-r", str(FPS), "-c:v", "h264_videotoolbox", "-b:v", q["bitrate"], "-pix_fmt", "yuv420p",
         "-video_track_timescale", "15360", str(seg["out"])])


def cmd_dung(args):
    need_ffmpeg()
    proj = resolve_project(args.du_an)
    data = load_project(proj)
    q = ({"name": "nhap", "size": (1280, 720), "bitrate": "4M"} if args.nhap
         else {"name": "1080p", "size": (1920, 1080), "bitrate": "12M"})
    q["cat"] = bool(data.get("cat_dau_sao", True))
    t_all = time.time()
    tr, wav = ensure_transcript(proj, data)
    words, times, scene_start, ratio = align(data, tr)
    total = tr["duration"] + TAIL
    xuat = proj / "xuat"
    xuat.mkdir(exist_ok=True)
    n_cues = write_srt(words, times, xuat / "phu-de.srt")
    spans = scene_times(data, times, scene_start, total)

    # lên danh sách đoạn hình
    seg_dir = proj / "build" / f"doan-{q['name']}"
    seg_dir.mkdir(parents=True, exist_ok=True)
    segs, report, g = [], [], 0
    for sc, (s, e) in zip(data["canh"], spans):
        dur = e - s
        media = media_for(proj, sc)
        warn = []
        if not media:
            media = [placeholder(proj, sc, q["size"])]
            warn.append("THIẾU ẢNH")
        # clip chuyển động giữ đúng độ dài gốc, ảnh tĩnh chia phần thời gian còn lại
        lens = [clip_len(m) if m.suffix.lower() in VID_EXT else None for m in media]
        n_img = sum(l is None for l in lens)
        clip_total = sum(l for l in lens if l)
        if n_img and clip_total <= dur - 3 * n_img:
            img_dur = (dur - clip_total) / n_img
            parts = [l if l else img_dur for l in lens]
        elif n_img:
            parts = [dur / len(media)] * len(media)
        else:
            parts = [dur * l / clip_total for l in lens]
        acc, frame_marks = s, [round(s * FPS)]
        for p_ in parts:
            acc += p_
            frame_marks.append(round(acc * FPS))
        if n_img and max(p for p, l in zip(parts, lens) if l is None) > LONG_IMAGE:
            warn.append(f"ảnh hiện {max(parts):.0f}s, nên thêm biến thể")
        for p_, l in zip(parts, lens):
            if l and p_ > l + 0.5:
                warn.append(f"clip dài {l:.0f}s nhưng phải lấp {p_:.0f}s (dừng hình ở cuối)")
        for k, m in enumerate(media):
            frames = frame_marks[k + 1] - frame_marks[k]
            if frames <= 0:
                continue
            effect = sc.get("hieu_ung") or EFFECTS[g % len(EFFECTS)]
            g += 1
            segs.append({"src": m, "frames": frames, "effect": effect})
        report.append((sc["so"], s, dur, len(media), warn))
    if segs:
        segs[0]["fade_in"] = True
        segs[-1]["fade_out"] = True
    for seg in segs:
        st = seg["src"].stat()
        key = (f"{seg['src']}|{st.st_size}|{st.st_mtime_ns}|{seg['frames']}|{seg['effect']}|"
               f"{seg.get('fade_in')}|{seg.get('fade_out')}|{q}")
        seg["out"] = seg_dir / (hashlib.sha1(key.encode()).hexdigest()[:20] + ".mp4")
    todo = [s for s in segs if not s["out"].exists()]
    print(f"🎬 Dựng {len(segs)} đoạn hình ({len(todo)} đoạn mới, {len(segs) - len(todo)} dùng lại)...")
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.luong) as ex:
        for _ in ex.map(lambda s: render_segment(s, q), todo):
            done += 1
            print(f"\r   {done}/{len(todo)}", end="", flush=True)
    if todo:
        print(f"\r   Xong {len(todo)} đoạn sau {time.time() - t0:.0f} giây")

    # ghép hình
    lst = proj / "build" / f"danh-sach-{q['name']}.txt"
    lst.write_text("".join("file '" + str(s["out"]).replace("'", "'\\''") + "'\n" for s in segs),
                   encoding="utf-8")
    video_only = proj / "build" / f"hinh-{q['name']}.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(video_only)])

    # trộn âm thanh
    print("🎵 Trộn giọng đọc và nhạc nền...")
    music = music_file(proj)
    T = f"{total:.3f}"
    voice = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11,"
             f"aresample=48000,apad=whole_dur={T},atrim=0:{T}")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_only), "-i", str(wav)]
    if music:
        vol = float(data.get("am_luong_nhac", 0.15))
        cmd += ["-stream_loop", "-1", "-i", str(music)]
        fc = (f"{voice},asplit=2[v1][v2];"
              f"[2:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{T},asetpts=PTS-STARTPTS,"
              f"volume={vol},afade=t=in:d=1.5,afade=t=out:st={total - 3:.3f}:d=3[m];"
              f"[m][v1]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=500[md];"
              f"[v2][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    else:
        fc = f"{voice}[a]"
    out = xuat / f"{data['du_an']}-{q['name']}.mp4"
    run(cmd + ["-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
               "-c:a", "aac", "-b:a", "192k", "-t", T, "-movflags", "+faststart", str(out)])

    # báo cáo
    lines = [f"Video: {out.name}   Thời lượng: {mmss(total)}   Phụ đề: {n_cues} dòng",
             f"Độ khớp giọng đọc / kịch bản: {ratio:.0%}", "",
             "Cảnh | Bắt đầu | Dài  | Số ảnh | Ghi chú"]
    for so, s, dur, nm, warn in report:
        lines.append(f"{so:>5} | {mmss(s):>7} | {dur:4.0f}s | {nm:>6} | {'; '.join(warn)}")
    (xuat / "bao-cao.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n✅ Xong sau {time.time() - t_all:.0f} giây: {out}")
    report_match(ratio)


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Dựng video tự động cho kênh YouTube")
    sub = ap.add_subparsers(dest="lenh", required=True)
    p = sub.add_parser("tao", help="tạo dự án mới từ kịch bản")
    p.add_argument("du_an", help="tên dự án, ví dụ 01-ten-video")
    p.add_argument("--kich-ban", required=True, help="đường dẫn file kịch bản .md")
    p.add_argument("--ghi-de", action="store_true", help="tạo lại bảng phân cảnh")
    p.set_defaults(fn=cmd_tao)
    p = sub.add_parser("trang-thai", help="xem cảnh nào đã có ảnh")
    p.add_argument("du_an")
    p.set_defaults(fn=cmd_trang_thai)
    p = sub.add_parser("phu-de", help="tạo phụ đề từ giọng đọc")
    p.add_argument("du_an")
    p.set_defaults(fn=cmd_phu_de)
    p = sub.add_parser("dung", help="dựng video")
    p.add_argument("du_an")
    p.add_argument("--nhap", action="store_true", help="bản xem nhanh 720p")
    p.add_argument("--luong", type=int, default=6, help="số đoạn dựng song song (mặc định 6)")
    p.set_defaults(fn=cmd_dung)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
