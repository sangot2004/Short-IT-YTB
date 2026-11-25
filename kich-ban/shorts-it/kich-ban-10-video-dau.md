# Kịch bản 10 Shorts đầu tiên — series "DE 30 giây"

Cách đọc kịch bản:
- **🎙 Lời** là phần đọc thành tiếng.
- **🖥 Hình** là thứ hiện trên màn hình.
- **[CHỮ]** là chữ to nổi trên video.

Thứ tự đăng gợi ý: đăng theo số thứ tự. Video 1 giới thiệu kênh, các video 2–6 là SQL (dễ lên view nhất), video 7–10 là kiến thức DE.

---

## Video 1 — Data Engineer thật ra làm gì?

**Tiêu đề:** Data Engineer làm gì? Giải thích trong 30 giây
**Hashtag:** #dataengineer #nghedulieu #it #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Data Engineer là gì mà lương cao vậy? Giải thích bằng một cái nhà hàng." | [CHỮ] DATA ENGINEER = ? · icon nhà hàng |
| 3–12s | "Dữ liệu giống như nguyên liệu: đến từ app, website, máy bán hàng… lộn xộn, bẩn, mỗi chỗ một kiểu." | Sơ đồ: app, web, POS → mũi tên → đống thùng lộn xộn |
| 12–25s | "Data Engineer là người làm hệ thống tự động gom nguyên liệu về, rửa sạch, sơ chế, xếp vào kho đúng chỗ. Ngày nào cũng chạy, không được hỏng." | Sơ đồ pipeline: Thu thập → Làm sạch → Kho dữ liệu, chữ "TỰ ĐỘNG mỗi ngày" |
| 25–35s | "Còn Data Analyst và Data Scientist là đầu bếp: lấy nguyên liệu sạch ra để nấu thành báo cáo và mô hình." | Kho → 2 đầu bếp: "Analyst: báo cáo", "Scientist: dự đoán" |
| 35–42s | "Không có Data Engineer, đầu bếp chẳng có gì để nấu. Mình đang học nghề này, follow để học cùng mình mỗi ngày." | [CHỮ] DE = người làm đường ống dữ liệu · nút Follow |

**Comment ghim:** "Bạn đang làm hoặc muốn làm vị trí nào trong ngành dữ liệu?"

---

## Video 2 — SQL không chạy theo thứ tự bạn viết

**Tiêu đề:** Câu SQL KHÔNG chạy từ trên xuống 😳
**Hashtag:** #sql #hocsql #dataengineer #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Tại sao câu SQL này lại báo lỗi?" | Code bên dưới, dòng WHERE gạch đỏ |
| 3–10s | "Mình đặt tên thanh_tien ở SELECT, rồi dùng nó ở WHERE, và database báo: không tìm thấy cột." | Thông báo lỗi `column "thanh_tien" does not exist` |
| 10–30s | "Vì SQL không chạy theo thứ tự bạn viết. Nó chạy FROM trước, rồi WHERE, GROUP BY, HAVING, sau đó mới tới SELECT, rồi ORDER BY và LIMIT. Lúc WHERE chạy, cái tên thanh_tien chưa hề tồn tại." | Thứ tự hiện lần lượt: **1 FROM → 2 WHERE → 3 GROUP BY → 4 HAVING → 5 SELECT → 6 ORDER BY → 7 LIMIT** |
| 30–38s | "Cách sửa: viết lại biểu thức trong WHERE. Còn ORDER BY chạy sau SELECT nên dùng tên mới thoải mái." | Code đã sửa, tích xanh |
| 38–42s | "Nhớ thứ tự này là bạn hiểu SQL hơn 80% người mới." | [CHỮ] FROM → WHERE → GROUP → HAVING → SELECT → ORDER |

```sql
-- ❌ Lỗi
SELECT gia * so_luong AS thanh_tien
FROM don_hang
WHERE thanh_tien > 100000;

-- ✅ Đúng
SELECT gia * so_luong AS thanh_tien
FROM don_hang
WHERE gia * so_luong > 100000
ORDER BY thanh_tien DESC;
```

> Ghi chú kiểm chứng: PostgreSQL, MySQL và SQL Server đều báo lỗi ở câu đầu. Một số hệ như Snowflake và DuckDB vẫn cho dùng alias trong WHERE, nên đừng nói "mọi database".

---

## Video 3 — WHERE vs HAVING

**Tiêu đề:** WHERE và HAVING khác gì nhau? (SQL)
**Hashtag:** #sql #phongvan #dataanalyst #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Câu hỏi phỏng vấn SQL kinh điển: WHERE và HAVING khác gì nhau?" | [CHỮ] WHERE vs HAVING |
| 3–15s | "WHERE lọc từng dòng, trước khi gom nhóm. Ví dụ: chỉ lấy đơn đã giao." | Bảng đơn hàng, các dòng "đã hủy" mờ đi |
| 15–28s | "HAVING lọc từng nhóm, sau khi gom nhóm. Ví dụ: chỉ lấy khách có tổng tiền trên 1 triệu." | Các nhóm khách hàng, nhóm dưới 1 triệu mờ đi |
| 28–38s | "Mẹo nhớ: điều kiện có hàm SUM, COUNT, AVG thì để ở HAVING. Còn lại để WHERE, vì lọc sớm thì chạy nhanh hơn." | Code bên dưới, highlight 2 dòng |
| 38–42s | "Lưu lại, đi phỏng vấn sẽ cần." | [CHỮ] WHERE = dòng · HAVING = nhóm |

```sql
SELECT khach_hang, SUM(tien) AS tong
FROM don_hang
WHERE trang_thai = 'da_giao'      -- lọc DÒNG
GROUP BY khach_hang
HAVING SUM(tien) > 1000000;       -- lọc NHÓM
```

---

## Video 4 — COUNT(*) vs COUNT(cột)

**Tiêu đề:** COUNT(*) và COUNT(cột) ra 2 kết quả khác nhau!
**Hashtag:** #sql #hocsql #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Cùng một bảng mà đếm ra 5 với 3. Sai ở đâu?" | [CHỮ] 5 ≠ 3 ?! |
| 3–12s | "Bảng khách hàng có 5 người, nhưng 2 người không để lại email." | Bảng 5 dòng, 2 ô email ghi NULL tô đỏ |
| 12–28s | "COUNT sao đếm tất cả các dòng, ra 5. COUNT email chỉ đếm những dòng có email, bỏ qua NULL, ra 3." | Code + kết quả 5 và 3 |
| 28–38s | "Muốn đếm số email không trùng thì dùng COUNT DISTINCT email. Báo cáo sai số liệu thường bắt đầu từ những chỗ nhỏ như thế này." | Dòng COUNT(DISTINCT email) |
| 38–42s | "Bạn có từng đếm nhầm thế này chưa? Comment cho mình biết." | [CHỮ] COUNT(cột) bỏ qua NULL |

```sql
SELECT
  COUNT(*)              AS so_dong,     -- 5
  COUNT(email)          AS co_email,    -- 3
  COUNT(DISTINCT email) AS email_khac   -- ≤ 3
FROM khach_hang;
```

---

## Video 5 — Bẫy NULL trong SQL

**Tiêu đề:** WHERE email = NULL luôn trả về 0 dòng — vì sao?
**Hashtag:** #sql #null #laptrinh #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Câu SQL này không báo lỗi, nhưng không bao giờ trả về dòng nào." | Code `WHERE email = NULL` → kết quả 0 rows |
| 3–15s | "Vì NULL không phải là giá trị. NULL nghĩa là không biết. Mà không biết so với không biết thì kết quả vẫn là… không biết, không phải đúng." | [CHỮ] NULL = "không biết" · NULL = NULL → ❓ |
| 15–28s | "Muốn tìm ô trống, phải dùng IS NULL. Muốn tìm ô có dữ liệu, dùng IS NOT NULL." | Code đúng, tích xanh |
| 28–38s | "Quy tắc: không bao giờ dùng dấu bằng hoặc khác với NULL." | [CHỮ] ❌ = NULL ✅ IS NULL |
| 38–42s | "Follow để không dính thêm bẫy SQL nào nữa." | |

```sql
-- ❌ luôn ra 0 dòng
SELECT * FROM khach_hang WHERE email = NULL;

-- ✅ đúng
SELECT * FROM khach_hang WHERE email IS NULL;
```

---

## Video 6 — LEFT JOIN làm bảng của bạn "phình to"

**Tiêu đề:** LEFT JOIN xong số dòng tăng lên? Đây là lý do
**Hashtag:** #sql #join #phongvan #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Bảng trái có 100 dòng, LEFT JOIN xong ra 130 dòng. Lỗi à?" | [CHỮ] 100 → 130 ?! |
| 3–15s | "Nhiều người nghĩ LEFT JOIN luôn giữ đúng số dòng của bảng trái. Sai. Nó chỉ đảm bảo không mất dòng nào thôi." | [CHỮ] Không mất ≠ không tăng |
| 15–30s | "Nếu một khách hàng có 3 đơn ở bảng phải, dòng khách đó sẽ bị nhân lên thành 3. Khóa nối bị trùng thì kết quả phình ra." | Hình: 1 dòng "An" nối với 3 dòng đơn hàng → 3 dòng "An" |
| 30–40s | "Trước khi join, hãy kiểm tra khóa bên phải có trùng không bằng GROUP BY … HAVING COUNT sao lớn hơn 1. Câu này hỏi phỏng vấn rất nhiều." | Code kiểm tra trùng |
| 40–43s | "Lưu video lại nhé." | |

```sql
-- Kiểm tra khóa bị trùng trước khi JOIN
SELECT khach_hang_id, COUNT(*)
FROM don_hang
GROUP BY khach_hang_id
HAVING COUNT(*) > 1;
```

---

## Video 7 — ETL vs ELT

**Tiêu đề:** ETL và ELT khác nhau đúng 1 chữ — và cả một thời đại
**Hashtag:** #dataengineer #etl #bigdata #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "ETL và ELT: chỉ đổi chỗ một chữ, nhưng khác cả cách làm." | [CHỮ] E-T-L vs E-L-T |
| 3–10s | "E là Extract, lấy dữ liệu. T là Transform, xử lý. L là Load, nạp vào kho." | 3 ô E / T / L |
| 10–22s | "ETL kiểu cũ: xử lý xong rồi mới nạp vào kho, vì ngày xưa kho dữ liệu đắt và yếu." | Nguồn → máy xử lý riêng → Kho |
| 22–35s | "ELT kiểu mới: nạp dữ liệu thô vào kho trước, rồi xử lý ngay trong kho bằng SQL. Kho trên cloud như BigQuery hay Snowflake đủ mạnh để làm việc đó. Công cụ hay dùng là dbt." | Nguồn → Kho (thô) → SQL/dbt → Bảng sạch |
| 35–42s | "Ngày nay phần lớn hệ thống mới đi theo ELT. Follow để xem video về dbt nhé." | [CHỮ] Xưa: ETL · Nay: ELT |

---

## Video 8 — Data Lake vs Data Warehouse

**Tiêu đề:** Data Lake và Data Warehouse — giải thích bằng cái tủ lạnh
**Hashtag:** #dataengineer #datalake #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Data Lake với Data Warehouse, giải thích bằng cái bếp nhà bạn." | [CHỮ] LAKE vs WAREHOUSE |
| 3–15s | "Data Lake là cái kho chứa: mua gì về cũng quăng vào, rau, thịt, thùng chưa mở. Rẻ, chứa được mọi thứ, nhưng tìm đồ thì mệt." | Kho bừa bộn: file log, ảnh, JSON, CSV |
| 15–27s | "Data Warehouse là tủ lạnh đã sơ chế: mọi thứ rửa sạch, chia hộp, dán nhãn. Lấy ra nấu ngay, nhưng chỉ chứa đồ đã chuẩn bị." | Tủ gọn gàng: các bảng có cột rõ ràng |
| 27–38s | "Còn Lakehouse là cố gắng có cả hai: chứa rẻ như lake, nhưng truy vấn gọn như warehouse. Databricks đang đi theo hướng này." | Hai hình gộp lại, [CHỮ] LAKEHOUSE |
| 38–42s | "Bạn muốn video sau giải thích Lakehouse kỹ hơn không?" | |

---

## Video 9 — Đừng lưu dữ liệu lớn bằng CSV

**Tiêu đề:** Data Engineer ít khi lưu CSV — họ dùng cái này
**Hashtag:** #python #parquet #dataengineer #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "Cùng một bảng dữ liệu, file này nhẹ hơn hẳn và đọc nhanh hơn. Bí mật là gì?" | Hai file: `ban_hang.csv` to, `ban_hang.parquet` nhỏ |
| 3–15s | "CSV lưu theo dòng, toàn là chữ. Muốn đọc một cột thì vẫn phải quét hết cả file." | Hình: dữ liệu xếp theo hàng ngang |
| 15–28s | "Parquet lưu theo cột, có nén, và nhớ luôn kiểu dữ liệu. Cần cột doanh thu thì chỉ đọc đúng cột đó." | Hình: dữ liệu xếp theo cột dọc, chỉ 1 cột sáng lên |
| 28–38s | "Với pandas, chỉ cần một dòng là đổi được. Thử với file của bạn rồi so dung lượng xem." | Code bên dưới |
| 38–42s | "Comment kết quả file của bạn giảm được bao nhiêu nhé." | [CHỮ] CSV → Parquet |

```python
import pandas as pd
df = pd.read_csv("ban_hang.csv")
df.to_parquet("ban_hang.parquet")   # cần: pip install pyarrow
```

> Trước khi quay, hãy tự chạy với file thật, rồi đưa đúng dung lượng thật lên màn hình. Không nêu con số "nhỏ hơn X lần" nếu chưa đo.

---

## Video 10 — File CSV quá lớn làm treo máy

**Tiêu đề:** File CSV 5GB làm treo máy? Dùng mẹo này trong pandas
**Hashtag:** #python #pandas #dataengineer #shorts

| Thời gian | 🎙 Lời | 🖥 Hình |
|---|---|---|
| 0–3s | "File CSV to hơn RAM, mở bằng pandas là máy đứng hình." | Màn hình loading xoay vòng, [CHỮ] MemoryError |
| 3–10s | "Đừng đọc cả file một lúc. Hãy đọc từng khúc." | [CHỮ] chunksize |
| 10–28s | "Thêm chunksize, pandas sẽ đọc mỗi lần 100 nghìn dòng. Xử lý xong khúc này mới đọc khúc tiếp theo, nên RAM chỉ cần chứa một khúc." | Code bên dưới, highlight `chunksize` |
| 28–38s | "Mẹo thêm: dùng usecols để chỉ đọc những cột cần, vừa nhanh vừa nhẹ." | Highlight `usecols` |
| 38–42s | "Còn nếu file to thật sự, đó là lúc cần đến Spark hoặc DuckDB. Follow để xem phần tiếp theo." | |

```python
import pandas as pd

tong = 0
for chunk in pd.read_csv("ban_hang.csv",
                         usecols=["doanh_thu"],
                         chunksize=100_000):
    tong += chunk["doanh_thu"].sum()
print(tong)
```

---

## Ý tưởng cho đợt tiếp theo (video 11–30)

- **SQL**: `UNION` vs `UNION ALL` · `ROW_NUMBER` vs `RANK` vs `DENSE_RANK` · window function trong 30 giây · tìm bản ghi trùng · CTE (`WITH`) · `NOT IN` gặp NULL · INDEX là gì
- **Python**: `apply` chậm và vectorize nhanh · DuckDB đọc thẳng CSV bằng SQL · virtual env để làm gì
- **DE**: batch vs streaming · Airflow là gì (bằng ví dụ báo thức) · partition dữ liệu · idempotent pipeline · Kafka giải thích bằng bưu điện · Star schema: bảng fact và dimension
- **Nghề**: lộ trình học DE 6 tháng · Data Analyst chuyển sang DE cần học gì · 5 câu phỏng vấn DE hay gặp
