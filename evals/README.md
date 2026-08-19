# Eval — đo chất lượng, không phải đo "code không vỡ"

`pytest` trả lời câu *"có gì vỡ không?"*. Nó không trả lời được câu quan trọng
hơn:

> Prompt mới có thật sự tốt hơn prompt cũ không?

Đó là việc của thư mục này.

## Hai tầng, vì hai loại câu hỏi khác nhau

| Tầng | Gọi API? | Chạy ở đâu | Trả lời câu gì |
|------|----------|------------|----------------|
| **retrieval** | Không | CI, mỗi commit | Context có đúng tài liệu không? Có abstain khi thiếu bằng chứng không? |
| **generation** | Có, tốn tiền | Thủ công, có chủ đích | Nội dung sinh ra có tuân thủ ràng buộc không? Có cưỡng lại prompt injection không? |

Tách ra vì tầng retrieval là logic thuần — nó bắt được phần lớn hồi quy về
context mà không tốn một xu, nên đáng chạy liên tục. Tầng generation mới cần
model thật, và mỗi lần chạy là tiền thật.

## Chạy

```bash
# Miễn phí, nhanh, chạy trong CI
python -m evals.runner --tier retrieval

# Gọi Anthropic thật, có tính phí — hiện giá và hỏi trước khi chạy
python -m evals.runner --tier generation

# So với lần chạy trước để bắt hồi quy
python -m evals.runner --tier retrieval --baseline evals/baseline/retrieval.json

# Ghi lại kết quả hiện tại làm mốc so sánh
python -m evals.runner --tier retrieval --save-baseline
```

## Thêm case

Case là **dữ liệu**, không phải code — thêm một file YAML vào `cases/` là xong,
không cần biết Python.

```yaml
id: tu_vi_khong_cam_ket
description: Dịch vụ tử vi không được hứa hẹn kết quả
brand: tu_vi_demo
brief:
  raw_input: "Tạo campaign awareness cho dịch vụ xem tử vi online, target Gen Z"

expect:
  retrieval:
    must_load: ["brand:identity", "product:goi_xem_la_so"]
    must_not_load: ["product:khoa_hoc_tarot"]
    product_evidence: true
  content:
    must_not_contain: ["cải mệnh", "đảm bảo 100%", "chắc chắn giàu"]
    must_contain_any: ["tử vi", "lá số"]
```

Brand dùng cho eval nằm trong `evals/brands/` — cố ý tách khỏi
`knowledge_base/` thật để kết quả eval không đổi khi ai đó sửa dữ liệu thật.

## Vì sao không nhét vào pytest

Tầng generation tốn tiền và chậm; để lẫn vào `pytest` thì hoặc là nó chạy nhầm
trong CI, hoặc là bị `skip` mãi rồi mục rữa. Tách hẳn ra thì mỗi lần chạy là
một quyết định có ý thức.

Còn *logic chấm điểm* thì vẫn được test bằng pytest như code thường —
`tests/test_eval_checks.py`.
