Bạn viết kịch bản video Shorts "Bản tin IT" bằng tiếng Việt có dấu cho một kênh YouTube/Facebook của người đang học Data Engineering.

Thư mục làm việc là thư mục hiện tại. Đọc HUONG-DAN.md (mục 3: cấu trúc file kịch bản, các loại thẻ, quy tắc viết) và xem kich-ban/mau-2026-11-25.json làm mẫu về cấu trúc và giọng văn.

Nguồn tin hôm nay: {TIN}
Ghi kịch bản vào: {RA}

Quy tắc:
- Chọn 3–4 tin IT/công nghệ đáng chú ý nhất cho dân kỹ thuật: hạ tầng, bảo mật, AI, dữ liệu, sự cố lớn, tin công nghệ Việt Nam. Bỏ tin bê bối đời tư, chính trị, khuyến mãi, quảng cáo sản phẩm, game giải trí thuần túy.
- Không lặp chủ đề chính đã có trong các file kich-ban/*.json khác của 3 ngày gần nhất (đọc chúng để kiểm tra).
- Tiêu đề và câu hook: mỗi con số phải đi đúng với tin của nó. KHÔNG ghép số liệu của tin này vào tên công ty/sự kiện của tin khác (ví dụ sai: "1Password bị xâm nhập, dữ liệu 21 triệu tài khoản" khi 21 triệu là của Character.AI).
- CHỈ dùng dữ kiện và con số có trong tiêu đề/tóm tắt tin. Không bịa, không đoán, không thêm số liệu ngoài nguồn. Không chắc thì viết chung chung hơn.
- 5–7 cảnh, tổng lời đọc 130–160 chữ (video khoảng 55–60 giây). Cảnh đầu loại "tieu_de" (hook gây tò mò), mỗi tin 1–2 cảnh với thẻ phù hợp ("so_lon" cho con số ấn tượng, "su_co" cho sự cố/lỗ hổng, "bang" cho danh sách, "tin" cho tin thường), cảnh cuối loại "ket" với MỘT câu nhận xét/bài học riêng cho dân kỹ thuật rồi "Follow để xem tin IT mỗi ngày nhé."
- Văn nói tự nhiên, câu ngắn. Không dùng emoji trên thẻ. Chữ trên thẻ ngắn gọn.
- "nhan": "Bản tin IT · DD/MM/YYYY".
- "nguon": mỗi tin một dòng "Tên báo: tiêu đề gốc — link".
- "dang": "tieu_de" dưới 70 ký tự có từ khóa; "mo_ta" tóm tắt các tin + dòng "Nguồn: ..." + dòng "Giọng đọc AI: VieNeu-TTS."; "hashtag" 4–6 cái gồm #tinIT #congnghe #shorts.
- File phải là JSON hợp lệ (dùng dấu ngoặc kép, không có chú thích).

{THEM}

Chỉ tạo/sửa đúng file {RA}. Không chạy lệnh, không sửa file nào khác. Xong thì trả lời ngắn: các tin đã chọn (mỗi tin một dòng).
