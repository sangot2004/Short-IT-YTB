#!/usr/bin/env python3
"""Kiểm tra chất lượng file giọng đọc trong du-an/<dự án>/giong/

Dùng:  ./cong-cu/kiem-tra-giong 01-ten-video
Báo: độ dài, tốc độ đọc, âm lượng, tiếng ồn nền, vỡ tiếng (clipping),
khoảng lặng đầu/cuối, và khoảng lặng dài bất thường giữa bài.
"""
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AUD = {".mp3", ".wav", ".m4a", ".aac", ".aiff", ".aif", ".flac", ".ogg", ".caf"}
SR = 16000
WIN = 0.1  # giây


def load(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(r.stderr.decode(errors="ignore")[-300:] or "không đọc được file")
    return np.frombuffer(r.stdout, dtype=np.float32)


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-9))


def words_for(proj, stem):
    m = re.match(r"^(\d+)", stem)
    if not m:
        return None
    for f in (proj / "thu-am").glob(f"{int(m.group(1)):02d}-*.txt"):
        body = f.read_text(encoding="utf-8").split("-" * 40, 1)[-1]
        return len(body.split())
    return None


def check(path, proj):
    x = load(path)
    dur = len(x) / SR
    n = int(WIN * SR)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = db(np.sqrt((frames ** 2).mean(axis=1)))
    speech = np.percentile(rms, 90)
    noise = np.percentile(rms, 5)
    quiet_share = float((rms < speech - 30).mean())  # tỉ lệ khung gần như im lặng
    peak = db(np.abs(x).max())
    clip = float((np.abs(x) > 0.99).mean()) * 100
    active = rms > speech - 25
    idx = np.where(active)[0]
    lead = idx[0] * WIN if len(idx) else dur
    tail = (len(rms) - 1 - idx[-1]) * WIN if len(idx) else dur
    # khoảng lặng dài giữa bài
    gaps, run = [], 0
    for i, a in enumerate(active):
        if not a:
            run += 1
        else:
            if run * WIN >= 3.0 and i - run > idx[0]:
                gaps.append(((i - run) * WIN, run * WIN))
            run = 0
    issues, notes = [], []
    if speech < -26:
        issues.append(f"Giọng nhỏ ({speech:.0f} dB): đưa micro gần hơn hoặc tăng mức thu")
    elif speech > -10:
        issues.append(f"Giọng quá to ({speech:.0f} dB): lùi micro ra hoặc giảm mức thu")
    if clip > 0.01:
        issues.append(f"Vỡ tiếng (đỉnh {peak:.1f} dB, {clip:.3f}% mẫu chạm trần): thu lại nhỏ hơn")
    elif peak > -1.0:
        notes.append(f"Đỉnh âm lượng sát trần ({peak:.1f} dB), chưa vỡ tiếng; công cụ dựng sẽ tự giảm đỉnh")
    snr = speech - noise
    if quiet_share < 0.02:
        notes.append("Gần như không có khoảng nghỉ nên không đo được tiếng ồn nền "
                     "(bình thường với giọng máy; với giọng thật hãy nghỉ ở dấu chấm)")
    elif snr < 22:
        issues.append(f"Tiếng ồn nền lớn (ồn {noise:.0f} dB, chênh giọng chỉ {snr:.0f} dB): "
                      "tắt quạt, điều hòa, đóng cửa, thu ở phòng nhiều đồ vải")
    elif snr < 30:
        notes.append(f"Tiếng ồn nền hơi cao (chênh giọng {snr:.0f} dB), vẫn dùng được, "
                     "lọc ồn trong CapCut nếu cần")
    if lead < 0.3:
        notes.append(f"Đầu file vào giọng ngay ({lead:.1f}s): công cụ dựng đã tự chèn khoảng nghỉ giữa các file")
    if tail < 0.3:
        notes.append(f"Cuối file cắt sát ({tail:.1f}s): công cụ dựng đã tự chèn khoảng nghỉ giữa các file")
    if lead > 3:
        notes.append(f"Đầu file có {lead:.0f}s yên lặng: nên cắt bớt")
    if tail > 4:
        notes.append(f"Cuối file có {tail:.0f}s yên lặng: nên cắt bớt")
    for t0, d in gaps:
        notes.append(f"Khoảng lặng {d:.0f}s tại {int(t0 // 60)}:{int(t0 % 60):02d}: có sót đoạn thu lại không?")
    w = words_for(proj, path.stem)
    pace = ""
    if w and dur > 5:
        wpm = w / ((dur - min(lead, 2) - min(tail, 2)) / 60)
        pace = f"{wpm:.0f} chữ/phút"
        if wpm > 200:
            notes.append(f"Đọc hơi nhanh ({wpm:.0f} chữ/phút): thử chậm lại, nghỉ ở dấu chấm (mục tiêu 150–180)")
        elif wpm < 120:
            notes.append(f"Đọc khá chậm ({wpm:.0f} chữ/phút): có thể tự nhiên hơn nếu nhanh hơn một chút")
    return dur, speech, noise, peak, pace, issues, notes


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    proj = Path(sys.argv[1]).expanduser()
    if not proj.exists():
        proj = ROOT / "du-an" / sys.argv[1]
    d = proj / "giong"
    files = sorted(p for p in d.iterdir() if p.suffix.lower() in AUD) if d.exists() else []
    if not files:
        sys.exit(f"❌ Chưa có file giọng đọc trong {d}")
    total, bad = 0.0, 0
    for p in files:
        try:
            dur, speech, noise, peak, pace, issues, notes = check(p, proj)
        except Exception as e:
            print(f"❌ {p.name}: {e}")
            bad += 1
            continue
        total += dur
        mark = "❌" if issues else ("⚠️ " if notes else "✅")
        bad += bool(issues)
        print(f"{mark} {p.name}")
        print(f"     {int(dur // 60)}:{int(dur % 60):02d}  | giọng {speech:.0f} dB | ồn nền {noise:.0f} dB"
              f" | đỉnh {peak:.1f} dB" + (f" | {pace}" if pace else ""))
        for s in issues:
            print(f"     ❌ {s}")
        for s in notes:
            print(f"     ⚠️  {s}")
    print(f"\nTổng: {len(files)} file, {int(total // 60)}:{int(total % 60):02d}"
          + ("  (cần thu lại các file bị ❌)" if bad else "  (không có lỗi nghiêm trọng)"))
    print("Mức tham khảo tốt: giọng khoảng -20 đến -12 dB, giọng hơn ồn nền từ 30 dB trở lên, không có mẫu chạm trần.")


if __name__ == "__main__":
    main()
