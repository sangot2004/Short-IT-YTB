# Công cụ Shorts bản tin IT — hướng dẫn

Mỗi ngày: **lấy tin RSS → Claude viết kịch bản → giọng AI VieNeu đọc → vẽ thẻ động → xuất video dọc 1080×1920 → bot Telegram gửi video + tiêu đề + mô tả cho bạn** → bạn kiểm tra và tự đăng.

## 1. Các lệnh

Chạy trong thư mục `cong-cu/shorts`:

| Việc | Lệnh |
|---|---|
| Lấy tin mới (30 giờ gần nhất) | `.venv/bin/python lay_tin.py` → `tin/<ngày>.md` |
| Dựng video | `.venv/bin/python ban_tin.py dung kich-ban/<ngày>.json` → `xuat/<ngày>.mp4` |
| Dựng nháp nhanh (15 fps) | thêm `--nhap` |
| Dựng rồi gửi Telegram | thêm `--gui` |
| Chỉ gửi lại Telegram | `.venv/bin/python ban_tin.py gui kich-ban/<ngày>.json` |
| Xem danh sách giọng | `.venv/bin/python ban_tin.py giong` |
| Tất cả trong một | `./chay-hang-ngay`: chưa có kịch bản thì lấy tin; có rồi thì dựng và gửi |

Một video dài khoảng 60 giây dựng mất khoảng 30 giây. Lần đầu mất thêm khoảng 40 giây để nạp mô hình giọng.

## 2. Cài bot Telegram (làm một lần, khoảng 3 phút)

1. Trên Telegram, mở **@BotFather** → gửi `/newbot` → đặt tên (ví dụ `Ban Tin IT cua toi`) và username, phải kết thúc bằng `bot`.
2. BotFather gửi lại một **token** dạng `123456789:AA...`. Không chia sẻ token này cho ai.
3. Trong thư mục `cong-cu/shorts`, sao chép `.env.example` thành `.env`. Mở `.env` và dán token vào sau `TELEGRAM_BOT_TOKEN=`.
4. Mở bot vừa tạo trên Telegram, bấm **Start**.
5. Chạy `.venv/bin/python ban_tin.py telegram-id`. Lệnh in ra chat id, bạn dán vào `TELEGRAM_CHAT_ID=` trong `.env`.
6. Thử gửi: `.venv/bin/python ban_tin.py gui kich-ban/mau-2026-11-25.json`.

Bot chỉ **gửi đi** cho bạn. Nó không chạy liên tục và không nhận lệnh, nên không cần máy chủ.

## 3. Cấu trúc file kịch bản `kich-ban/<ngày>.json`

```json
{
  "nhan": "Bản tin IT · 25/11/2026",
  "giong": "Minh Đức",                       // tùy chọn, mặc định theo cau-hinh.json
  "canh": [
    {"loi": "lời đọc + phụ đề", "doc": "(tùy chọn) cách đọc riêng", "the": { ...thẻ... }}
  ],
  "nguon": ["Báo: tiêu đề bài gốc", "..."],   // gửi kèm Telegram để bạn kiểm tra
  "dang": {"tieu_de": "...", "mo_ta": "...", "hashtag": ["#tinIT", "#shorts"]}
}
```

**Các loại thẻ** (`"loai"`):

| loai | Trường | Dùng khi |
|---|---|---|
| `tieu_de` | `tren`, `chinh`, `duoi`, `mau` | Cảnh mở đầu (hook) |
| `so_lon` | `so` (ví dụ `"45%"`, `"7,4 triệu"`; số tự đếm lên), `nhan`, `phu`, `mau` | Tin có con số ấn tượng |
| `su_co` | `ten`, `ngay`, `trang_thai`, `chi_tiet`, `mau` | Sự cố, lỗ hổng, sập dịch vụ |
| `bang` | `tieu_de`, `cot` [2 cột], `dong` [[trái, phải, màu], ...], `ghi_chu` | Danh sách: dịch vụ, giá, so sánh |
| `tin` | `nguon`, `tieu_de`, `y` [ý chính...] | Tin thường |
| `code` | `tieu_de`, `code` (xuống dòng bằng `\n`, tối đa 10 dòng) | Mẹo SQL/Python |
| `ket` | `chinh`, `phu` (có nút FOLLOW) | Cảnh kết + bài học |

Màu (`mau`): `do`, `vang`, `xanh`, `tim`, `lam`, `xam`.

**Quy tắc viết:**
- 5–7 cảnh, mỗi cảnh 1–2 câu. Tổng 130–160 chữ thì video dài khoảng 55–60 giây.
- Cảnh cuối luôn có **một câu nhận xét / bài học của kênh**. Đây là phần giá trị riêng, giúp video không bị coi là "chỉ đọc lại tin".
- Chỉ dùng dữ kiện có trong bài gốc. Không thêm số liệu tự đoán.
- Không dùng emoji trên thẻ, vì font không hiển thị được.

## 4. Cấu hình `cau-hinh.json` (tùy chọn)

```json
{
  "ten_kenh": "Bản Tin IT",
  "giong": "Minh Đức",
  "toc_do": 1.1,
  "nghi_giua_canh": 0.25,
  "nhac_nen": "/đường/dẫn/nhac.mp3",
  "am_luong_nhac": 0.08,
  "phat_am": {"Kubernetes": "cu bơ nét tít"}
}
```

`phat_am` chỉ đổi cách **đọc**, phụ đề vẫn giữ chữ gốc. Mặc định đã có `IT → ai ti`, `DRAM → đi ram`, `TP HCM → Thành phố Hồ Chí Minh`.

## 5. Giọng đọc và giấy phép

- Giọng đọc dùng **VieNeu-TTS v3 Turbo** (github.com/pnnbao97/VieNeu-TTS), chạy hoàn toàn trên máy, miễn phí.
- Theo model card trên Hugging Face, mô hình và các giọng có sẵn dùng **Apache-2.0**, và âm thanh tạo ra **được dùng thương mại, bật kiếm tiền**.
- Nên ghi "Giọng đọc AI: VieNeu-TTS" trong mô tả video.
- Không dùng tính năng nhân bản giọng (voice cloning) với giọng người thật khi chưa được họ cho phép.

## 6. Trước khi đăng: kiểm tra 1 phút

1. Xem video trên Telegram. Đối chiếu các con số với danh sách "NGUỒN" bot gửi kèm.
2. Nếu có chỗ sai: sửa file kịch bản → `dung ... --gui` lại. Giọng đã tạo được lưu sẵn, nên chỉ cảnh bị sửa mới phải đọc lại.
3. Khi đăng YouTube: chọn **Có** ở câu hỏi nội dung dùng AI hoặc nội dung chỉnh sửa.

## 7. Điều khiển bằng lệnh Telegram

Bot chạy nền trên Mac (tự bật lại khi khởi động máy). Chỉ chat của bạn (`TELEGRAM_CHAT_ID`) mới ra lệnh được.

| Lệnh | Làm gì |
|---|---|
| `/lam` | Làm video hôm nay. Nếu đã có thì gửi lại. |
| `/lam_moi` | Lưu kịch bản cũ, Claude viết kịch bản MỚI từ tin mới nhất, dựng và gửi. |
| `/sua <yêu cầu>` | Claude sửa kịch bản hôm nay theo yêu cầu (ví dụ `/sua bỏ tin số 3, hook giật gân hơn`), dựng và gửi lại. |
| `/tin` | Gửi 15 tiêu đề tin IT mới nhất. |
| `/giong [tên]` | Xem hoặc đổi giọng đọc (ví dụ `/giong Mai Anh`). |
| `/dang [HH:MM]` | Tải video hôm nay lên YouTube, hẹn công khai 19:30 (hoặc giờ ghi kèm). Xem mục 8. |
| `/trang_thai` | Bot đang làm gì, hôm nay đã có video chưa. |

- Claude được gọi qua lệnh `claude` (model Sonnet, đổi bằng `"model_claude"` trong `cau-hinh.json`). Nó chỉ được đọc file và ghi vào `kich-ban/`, không được chạy lệnh hay lên mạng.
- Mỗi lần viết kịch bản mất khoảng 30 giây và tính vào hạn mức gói Claude của bạn. Dựng video mất khoảng 1 phút.
- Mac phải bật và không ngủ thì bot mới trả lời. Gập máy thì bot dừng, mở lại thì bot chạy tiếp.

Bật/tắt bot:

```bash
./bot-nen bat     # bật
./bot-nen tat     # tắt hẳn
./bot-nen xem     # trạng thái + nhật ký (tam/bot.log)
```

## 8. Đăng thẳng lên YouTube bằng `/dang`

`/dang` dùng YouTube Data API (`dang_ytb.py`): tải video hôm nay lên kênh ở chế độ Riêng tư, hẹn công khai lúc 19:30 giờ VN (đổi mặc định bằng `"gio_dang"` trong `cau-hinh.json`, hoặc gõ `/dang 20:00`). Nếu lúc gõ lệnh đã qua giờ hẹn, video được hẹn 15 phút sau. Muốn huỷ: YouTube Studio → Nội dung → Shorts → đổi về Riêng tư hoặc xoá.

- Bot không tải trùng: video đã đăng được ghi vào `xuat/<ngày>-ytb.json`. `/dang lai` để tải thêm bản nữa.
- Tự khai báo sẵn: không dành cho trẻ em, có dùng AI (giọng đọc), tiếng Việt, danh mục Khoa học và công nghệ.
- Hạn mức API miễn phí 10.000 đơn vị/ngày, mỗi lần tải lên tốn khoảng 1.600, đủ cho vài video/ngày.

### Quan trọng: Google phải duyệt project trước

Video tải lên từ project Google Cloud **chưa qua audit** của YouTube bị **khoá ở chế độ Riêng tư** (không công khai được, kể cả đổi tay). Vì vậy `/dang` sẽ từ chối cho đến khi bạn đặt `"ytb_api_da_duyet": true` trong `cau-hinh.json`. Trong lúc chờ, `/dang thu` tải lên Riêng tư để kiểm tra đường đi (xoá video thử sau đó), còn đăng thật thì nhờ Claude qua chat.

### Cài đặt một lần (khoảng 15 phút, dùng tài khoản Google có kênh Bản Tin IT — Chrome profile Thịnh)

**Trạng thái (26/11/2026):** bước 1–3 và 5 đã xong. Project `ban-tin-it` thuộc tài khoản Google của kênh (Nguyễn Thịnh). YouTube Data API v3 đã bật. Màn hình đồng ý ở chế độ **Thử nghiệm**, với chính tài khoản đó là người dùng thử. OAuth client `ban-tin-it-bot` (Desktop) đã lưu thành `google-oauth.json`. Vì còn ở chế độ Thử nghiệm, phiên đăng nhập hết hạn sau 7 ngày: khi bot báo "hết hạn", chạy lại `dang_ytb.py dang-nhap`. Muốn chuyển sang In production, Google yêu cầu trang chủ và link chính sách bảo mật công khai trên trang *Branding*.

1. Vào https://console.cloud.google.com → tạo project mới, ví dụ `ban-tin-it`.
2. **APIs & Services → Library** → tìm **YouTube Data API v3** → **Enable**.
3. **Google Auth Platform** (OAuth consent screen) → **Get started**: tên app `Ban Tin IT uploader`, email hỗ trợ là Gmail của bạn, chọn **External**.
4. Mục **Audience** → **Publish app** (chuyển sang *In production*). Nếu để *Testing*, phiên đăng nhập tự hết hạn sau 7 ngày. App chưa được Google xác minh vẫn dùng được cho chính bạn (lúc đăng nhập bấm *Advanced → Go to … (unsafe)*, vì đây là app của bạn).
5. Mục **Clients** → **Create client** → loại **Desktop app** → tạo → **Download JSON**. Đổi tên file thành `google-oauth.json` và đặt vào thư mục `cong-cu/shorts/`. File này là bí mật, đã nằm trong `.gitignore`.
6. Đăng nhập một lần trên Mac:
   ```bash
   .venv/bin/python dang_ytb.py dang-nhap
   ```
   Trình duyệt mở ra → chọn đúng tài khoản và **chọn kênh Bản Tin IT** nếu được hỏi → cho phép. Lệnh in ra tên kênh để bạn kiểm tra. Phiên đăng nhập lưu ở `.ytb-token.json`.
7. Thử: gõ `/dang thu` trên Telegram → video Riêng tư xuất hiện trong Studio → xoá đi.
8. Xin duyệt: điền form **YouTube API Services – Audit and Quota Extension** tại https://support.google.com/youtube/contact/yt_api_form. Mô tả thật: công cụ cá nhân, chỉ tải video do chính mình làm lên kênh của mình, mỗi ngày 1 Short, không thu thập dữ liệu người khác. Google trả lời qua email, thường mất vài tuần.
9. Khi được duyệt: thêm `"ytb_api_da_duyet": true` vào `cau-hinh.json`. Từ đó `/dang` đăng thật.
