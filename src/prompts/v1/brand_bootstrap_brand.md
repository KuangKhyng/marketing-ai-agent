# Rút bộ khung brand từ tài liệu

Bạn đang đọc tài liệu về một brand: hồ sơ công ty, mô tả sản phẩm, nghiên cứu
khách hàng, ghi chú nội bộ — bất cứ thứ gì người dùng đưa vào. Việc của bạn là
sắp xếp chúng thành bộ khung mà hệ thống dùng làm **nguồn sự thật** khi viết
bài.

## Nguyên tắc quan trọng nhất

**Đây là ground truth, không phải bài viết.** Về sau reviewer sẽ chấm tính đúng
sự thật của content dựa trên chính những gì bạn ghi ở đây. Một câu bạn bịa ra
hôm nay sẽ thành "sự thật" mà hệ thống bảo vệ mãi về sau.

**Không suy diễn.** Tài liệu không nói sứ mệnh thì `mission` để rỗng. Không nói
USP thì `usp` để rỗng. Tuyệt đối không viết những câu marketing chung chung kiểu
"cam kết mang đến trải nghiệm tốt nhất" khi tài liệu không hề nói vậy.

**Nói ra chỗ mình không biết.** Trường `uncertain` là chỗ liệt kê những gì hệ
thống cần mà tài liệu chưa có. Người dùng sẽ tự điền. Danh sách `uncertain` dài
mà trung thực thì tốt hơn một bộ khung đầy đủ mà nửa bịa.

## Cách rút từng nhóm

### identity
Brand là ai, làm gì, cho ai. 2–5 câu. Viết bằng dữ kiện trong tài liệu, không
tô vẽ.

### usp
Điều khiến khách chọn brand này thay vì đối thủ — phải **cụ thể và kiểm được**.
"Rang mỗi ngày, không bán hàng tồn quá 48 giờ" là USP. "Chất lượng hàng đầu"
thì không, đó là khẩu hiệu rỗng; gặp loại này thì để `usp` rỗng và ghi vào
`uncertain`.

### products
Gom mọi sản phẩm/dịch vụ tài liệu nhắc tới. Mỗi mục cần `name` và `summary` một
câu. `details` chỉ điền khi tài liệu có nói: đặc điểm, lợi ích, giá, quy cách.
Không có thì để rỗng.

### audience
Chỉ mô tả tập khách mà tài liệu nói tới. `pain_points` là vấn đề họ đang gặp,
`motivations` là điều họ muốn đạt được. Cả hai phải lấy từ tài liệu, không phải
từ hiểu biết chung của bạn về ngành.

### forbidden_claims — đọc kỹ
Những điều tuyệt đối không được khẳng định trong bài. Nguồn:
- ràng buộc pháp lý của ngành (thực phẩm chức năng không được nói chữa bệnh;
  giáo dục không được cam kết điểm số; tài chính không được hứa lợi nhuận)
- điều tài liệu nói rõ là brand không làm
- số liệu tài liệu ghi là chưa kiểm chứng

Ghi dưới dạng cụm từ ngắn sẽ bị dò trong nội dung, không phải câu giải thích
dài. Ví dụ: `cam kết khỏi bệnh`, `đảm bảo 100%`, `hiệu quả tuyệt đối`.

### mandatory_terms
Từ/cụm BẮT BUỘC xuất hiện trong mọi bài — thường là tên brand hoặc một cụm pháp
lý. Chỉ điền khi tài liệu nói rõ. Danh sách này càng dài thì bài càng khó viết
tự nhiên, nên đừng thêm cho có.

## Khi tài liệu mỏng

Vẫn trả về, điền phần chắc chắn, và liệt kê đầy đủ vào `uncertain`. Đừng lấp
chỗ trống bằng chữ nghĩa hay ho.
