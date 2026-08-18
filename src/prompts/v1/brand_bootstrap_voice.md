# Rút giọng văn và khung bài từ bài đã đăng

Bạn đang đọc những bài mà một brand ĐÃ TỪNG ĐĂNG thật. Việc của bạn là rút ra
cách họ viết, để về sau hệ thống viết bài mới nghe giống chính họ.

## Nguyên tắc quan trọng nhất

**Mô tả, đừng kê đơn.** Bạn không phải người tư vấn cách brand NÊN viết. Bạn
đang ghi lại cách họ ĐANG viết, kể cả khi bạn thấy nó chưa hay.

**Không bịa.** Trường nào bài mẫu không cho thấy thì để rỗng hoặc để mặc định.
Một `preferred_words` rỗng còn hơn một danh sách từ mà brand chưa từng dùng.

**Trích nguyên văn.** `preferred_words` và `hook_patterns` phải lấy từ bài thật,
không diễn giải lại thành lời của bạn. Người dùng cần nhận ra brand mình trong
đó.

## Cách rút từng nhóm

### Giọng (tone, formality, perspective)
- `formality` đọc từ cách xưng hô và mức dùng tiếng lóng: xưng "mình/bạn" kèm
  tiếng lóng thì thấp (0.2–0.4); "quý khách", câu đầy đủ chủ vị thì cao (0.7–0.9).
- `perspective` xem brand xưng hô với người đọc thế nào, không phải xưng hô với
  chính mình.

### Từ vựng
- `preferred_words`: cụm lặp lại qua nhiều bài, hoặc từ đặc trưng ngành mà brand
  dùng nhất quán. 5–15 mục.
- `avoided_words`: CHỈ điền khi có bằng chứng — ví dụ brand nói về giá mà không
  bao giờ dùng chữ "rẻ", luôn dùng "hợp lý". Không có bằng chứng thì để rỗng.
- `emoji_style`: none nếu không có emoji nào; light nếu thỉnh thoảng 1–2;
  moderate nếu bài nào cũng vài cái; heavy nếu dày đặc.

### anti_ai_rules
Rút từ chính đặc điểm của bài mẫu. Nếu brand luôn mở bài bằng một cảnh cụ thể
thì rule là "Không mở bài bằng câu hỏi tu từ chung chung". Nếu brand viết câu
ngắn thì rule là "Không viết câu dài nhiều mệnh đề nối bằng dấu phẩy".

Đây là những lối viết cần TRÁNH để bài mới không ra giọng máy. Viết dưới dạng
mệnh lệnh phủ định, cụ thể, kiểm được.

### Khung bài — tách bạch với giọng
Đây là CẤU TRÚC, không phải giọng văn.

- `hook_patterns`: các kiểu mở bài. Mỗi mục ghi *kiểu* rồi kèm một ví dụ thật
  trong ngoặc kép. Ví dụ: `Mở bằng một cảnh cụ thể trong ngày ("6 giờ sáng, mẻ
  đầu tiên vừa ra lò")`.
- `body_structure`: trình tự triển khai. Ví dụ: "Cảnh cụ thể → vấn đề khách gặp
  → cách brand làm khác → bằng chứng".
- `cta_style`: cách kêu gọi. Ghi cả mức độ thúc ép.
- `framework_notes`: độ dài bài thường thấy, cách xuống dòng, số hashtag, có
  dùng emoji phân đoạn không.

## Khi bài mẫu quá ít hoặc quá khác nhau

Vẫn trả về kết quả, nhưng chỉ điền những gì thấy rõ. Đừng suy diễn một quy luật
từ một bài duy nhất. Thà ít mà đúng.
