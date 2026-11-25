# Học kiếm tiền — công cụ làm video

| Thư mục | Nội dung |
|---|---|
| `cong-cu/` | Công cụ dựng video dài 16:9 (giọng đọc + ảnh + phụ đề Whisper). Xem `cong-cu/HUONG-DAN.md`. |
| `cong-cu/shorts/` | Shorts **bản tin IT** 9:16 hằng ngày: lấy tin RSS → Claude viết kịch bản → giọng AI VieNeu-TTS → dựng video → bot Telegram. Xem `cong-cu/shorts/HUONG-DAN.md`. |
| `kich-ban/shorts-it/` | Cách làm nội dung và kịch bản 10 Shorts "DE 30 giây". |

## Cài lại trên máy mới

```bash
cd cong-cu/shorts
python3.12 -m venv .venv
.venv/bin/pip install vieneu feedparser pillow requests fonttools
cp .env.example .env   # rồi điền TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

Cần thêm: `ffmpeg` (brew), lệnh `claude` (Claude Code) cho bot Telegram, macOS (dùng font Helvetica Neue có sẵn).
