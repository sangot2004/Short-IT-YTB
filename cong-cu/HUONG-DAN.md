# Hướng dẫn dùng công cụ dựng video tự động

Công cụ này nhận **ảnh, clip chuyển động, giọng đọc và nhạc nền**, rồi tự làm phần còn lại:
- Nghe giọng đọc bằng Whisper (chạy ngay trên máy, không gửi dữ liệu đi đâu) và khớp từng chữ với kịch bản.
- Đổi ảnh đúng lúc lời đọc chuyển sang cảnh mới.
- Thêm hiệu ứng zoom và lia chậm cho ảnh tĩnh.
- Trộn nhạc nền: tự giảm âm lượng nhạc khi có lời đọc, cân bằng âm lượng giọng.
- Xuất video MP4 1080p và **phụ đề .srt đúng chính tả theo kịch bản**.

Đã chạy thử trên máy này (Mac M2 Pro): với video 9,5 phút, phụ đề mất khoảng 1 phút, bản xem nhanh khoảng 1 phút, bản 1080p khoảng 2 phút.

---

## Cấu trúc thư mục

```
học kiếm tiền/
├── cong-cu/            ← công cụ (không cần đụng vào)
│   └── vd              ← lệnh để chạy
├── kich-ban/           ← kịch bản và file prompt
└── du-an/
    └── 01-ten-video/   ← mỗi video là một thư mục
        ├── anh/        ← BỎ ẢNH VÀ CLIP VÀO ĐÂY
        ├── giong/      ← BỎ FILE GIỌNG ĐỌC VÀO ĐÂY
        ├── nhac/       ← BỎ 1 FILE NHẠC NỀN VÀO ĐÂY (không bắt buộc)
        ├── xuat/       ← VIDEO, PHỤ ĐỀ VÀ BÁO CÁO XUẤT RA Ở ĐÂY
        ├── phan-canh.yaml  ← bảng phân cảnh (sửa được)
        └── loi-doc.txt     ← lời đọc để bạn cầm đọc khi thu âm
```

Mỗi video mới tạo bằng lệnh `tao` (xem mục **Các lệnh**), rồi bỏ ảnh và giọng vào thư mục của nó.

---

## Các lệnh

Mở Terminal, rồi chạy lệnh dưới đây để vào thư mục làm việc:
```bash
cd ~/Documents/Learn_DE/"học kiếm tiền"
```

**Xem cảnh nào đã có ảnh, cảnh nào còn thiếu:**
```bash
./cong-cu/vd trang-thai 01-ten-video
```

**Dựng bản xem nhanh 720p** (để kiểm tra trước):
```bash
./cong-cu/vd dung 01-ten-video --nhap
```

**Dựng bản hoàn chỉnh 1080p** (để đăng YouTube):
```bash
./cong-cu/vd dung 01-ten-video
```

**Chỉ tạo phụ đề:**
```bash
./cong-cu/vd phu-de 01-ten-video
```

**Tạo dự án cho video mới** (ví dụ video Lý Mạc Sầu):
```bash
./cong-cu/vd tao 02-ly-mac-sau --kich-ban kich-ban/02-ly-mac-sau.md
```
> Kịch bản phải theo đúng định dạng: mỗi chương bắt đầu bằng `## 0:00 – ...`, mỗi cảnh có một dòng `[HÌNH: ...]`, và phần cuối bắt đầu bằng `## GÓI ĐĂNG VIDEO`.

Mẹo: khi bạn thay một vài ảnh rồi dựng lại, công cụ **chỉ dựng lại những đoạn bị thay đổi**, nên lần sau nhanh hơn nhiều.

---

## Quy trình cho mỗi video

### Bước 1: Thu giọng đọc
- Đọc theo file `loi-doc.txt`. Các dòng `[Cảnh 1]`, `[Cảnh 2]`… chỉ để bạn biết mình đang ở đâu, **không đọc ra**.
- Có thể thu **một file duy nhất** hoặc **nhiều file** (01.m4a, 02.m4a…). Công cụ ghép theo thứ tự tên file.
- Định dạng được hỗ trợ: m4a (ghi âm iPhone), mp3, wav, aiff, flac.
- Đọc sai thì cứ đọc lại câu đó rồi **cắt đoạn sai đi trước khi bỏ vào** giong/. Nếu bạn cố ý đọc khác kịch bản, hãy sửa phần `loi` trong `phan-canh.yaml` cho khớp, để phụ đề đúng.

### Bước 2: Đặt tên ảnh và clip
Mỗi cảnh lấy **mọi file có tên bắt đầu bằng `canh-<số cảnh 2 chữ số>`**, rồi xếp theo thứ tự tên. Để chắc chắn thứ tự, hãy đặt tên theo dạng **`canh-01-1`, `canh-01-2`, `canh-01-3`**.

- **Ảnh tĩnh** (png, jpg, webp): công cụ tự chia đều thời gian còn lại của cảnh và thêm hiệu ứng zoom hoặc lia.
- **Clip chuyển động** (mp4, mov): giữ đúng độ dài gốc. Nếu cảnh dài hơn clip mà không có ảnh nào khác, clip sẽ dừng hình ở khung cuối.
- Ảnh không đúng khổ 16:9 vẫn dùng được: công cụ tự cắt phần giữa cho vừa khung.
- **Cảnh chưa có ảnh** sẽ hiện khung "THIẾU ẢNH · CẢNH n" kèm mô tả. Nhờ vậy bạn vẫn dựng thử được khi chưa đủ ảnh.

**Ví dụ đặt tên:** cảnh 1 có 2 ảnh và 1 clip → `canh-01-1.png`, `canh-01-2.mp4`, `canh-01-3.png`; cảnh 2 chỉ 1 ảnh → `canh-02-1.png`.

> Nếu báo cáo ghi **"ảnh hiện 25s, nên thêm biến thể"**, nghĩa là cảnh đó dài mà ít ảnh, người xem dễ chán. Hãy tạo thêm 1–2 ảnh khác góc rồi đặt tên tiếp, ví dụ `canh-03-2.png`.

### Bước 3: Nhạc nền (không bắt buộc)
- Bỏ **một file** nhạc vào `nhac/`. Nhạc tự lặp lại nếu ngắn hơn video, và tự nhỏ đi khi có lời đọc.
- Nên lấy nhạc từ **YouTube Audio Library** (miễn phí, an toàn bản quyền).
- Muốn nhạc to hay nhỏ hơn: sửa dòng `am_luong_nhac: 0.15` trong `phan-canh.yaml` (0.1 là nhỏ hơn, 0.25 là to hơn).

### Bước 4: Dựng và kiểm tra
1. Chạy `trang-thai` để xem còn thiếu gì.
2. Dựng bản `--nhap`, xem lại toàn bộ video.
3. Đọc `xuat/bao-cao.txt`: thời điểm bắt đầu và độ dài từng cảnh, kèm cảnh báo.
4. Sửa hoặc thêm ảnh nếu cần, dựng lại.
5. Dựng bản 1080p.

### Bước 5: Đăng YouTube
- Video: `xuat/01-ten-video-1080p.mp4`
- Phụ đề: `xuat/phu-de.srt`. Tải lên trong YouTube Studio, mục **Phụ đề**, chọn **Tải tệp lên** và **Có thời gian**.
- Muốn tinh chỉnh thêm (chuyển cảnh, hiệu ứng chữ…), có thể mở file MP4 trong CapCut và nhập file .srt vào.

---

## Tuỳ chỉnh trong `phan-canh.yaml`

```yaml
- so: 5
  mo_ta: Đảo Đào Hoa, hoa đào bay...
  anh:
  - canh-05*          # có thể ghi cụ thể: canh-05-1.png, dao-hoa.jpg ...
  hieu_ung: vao       # tuỳ chọn: vao | ra | trai | phai | tinh
  loi: |-
    Lời đọc của cảnh 5...
```
- `hieu_ung`: không ghi thì công cụ tự luân phiên các hiệu ứng. Ghi `tinh` để ảnh đứng yên.
- `anh`: được ghi nhiều dòng; được dùng tên file bất kỳ trong `anh/`.

---

## Khi gặp lỗi
- **"Độ khớp thấp"**: bạn đọc khác kịch bản nhiều, hoặc nhầm file giọng. Kiểm tra lại `giong/` và phần `loi` trong yaml.
- **Chuyển cảnh lệch vài giây**: sửa phần `loi` cho đúng câu bạn đã đọc ở đầu cảnh đó.
- **Lỗi khác**: chụp hoặc copy thông báo lỗi gửi cho Claude.
- Lần đầu chạy phụ đề, công cụ tải mô hình Whisper khoảng 1,6 GB. Mô hình đã được tải sẵn trên máy này.

---

## Dấu ngôi sao nhỏ của Gemini

Mặc định công cụ **cắt viền phải 4% và viền dưới 5,5%** của mọi ảnh và clip trước khi dựng, để che dấu ngôi sao Gemini gắn ở góc.

- ✅ Có tác dụng với **ảnh gốc tải bằng nút mũi tên** (2752×1536), vì ngôi sao nằm sát góc.
- ❌ **Không đủ với ảnh WebP 1024 px lưu từ bản xem trước**: ngôi sao nằm sâu trong khung hình (cách mép phải khoảng 9%, mép dưới khoảng 15%). Muốn hết ngôi sao với những ảnh này thì phải tải lại bản gốc.
- Muốn tắt tính năng cắt viền, thêm dòng `cat_dau_sao: false` vào `phan-canh.yaml`.
