# Marketing Agent — Knowledge Base Management UI

## Overview

Trang quản lý Knowledge Base riêng biệt, cho phép user:
- Tạo brand mới
- Thêm/sửa/xóa documents cho từng brand
- Edit voice profile
- Quản lý brand settings (forbidden claims, mandatory terms, etc.)

---

## 1. Navigation

Thêm vào sidebar 1 link cố định (luôn hiện, không phụ thuộc campaign phase):

```
Sidebar:
┌─────────────────────┐
│ ✦ Marketing Agent   │
│                     │
│ Campaign Phases:    │
│   ▶️ Input           │
│   ⬜ Brief Review    │
│   ⬜ Strategy Review │
│   ⬜ Content Review  │
│   ⬜ Final Review    │
│   ⬜ Export          │
│                     │
│ ─────────────────── │
│ 📚 Knowledge Base   │  ← NEW: link cố định
│ + New Campaign      │
│                     │
│ History:            │
│   ...               │
└─────────────────────┘
```

Click "📚 Knowledge Base" → chuyển sang trang quản lý.

---

## 2. Trang Knowledge Base — Brand List

**URL:** `/knowledge`

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  📚 Knowledge Base                          [+ Tạo Brand Mới]   │
│  Quản lý brand knowledge cho campaigns                          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ✦ TửViOnline                                    5 docs   │  │
│  │  Nền tảng xem tử vi online cho Gen Z          ●●●●●○○○   │  │
│  │                                       [Mở]  [Xóa]        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ☕ Coffee Shop ABC                              3 docs   │  │
│  │  Quán cà phê specialty tại quận 1             ●●●○○○○○   │  │
│  │                                       [Mở]  [Xóa]        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │
│  │                                                           │  │
│  │       Chưa có brand nào.                                  │  │
│  │       Bấm "Tạo Brand Mới" để bắt đầu.                    │  │
│  │                                                           │  │
│  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │
│                                                                  │
│  Completeness bar: hiện % knowledge đã fill                      │
│  (identity + tone + ít nhất 1 product + 1 audience = 100%)       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Completeness Score

Mỗi brand có thanh completeness dựa trên:
- Brand identity (identity.md) có content? → 25%
- Tone of voice (tone_of_voice.md) có content? → 25%
- Ít nhất 1 product document? → 25%
- Ít nhất 1 audience document? → 25%

Giúp user biết brand nào cần thêm knowledge.

---

## 3. Modal: Tạo Brand Mới

Khi bấm "+ Tạo Brand Mới", hiện modal:

```
┌──────────────────────────────────────────────┐
│  Tạo Brand Mới                          [X]  │
│                                              │
│  Brand ID *                                  │
│  ┌────────────────────────────────────────┐  │
│  │ coffee_shop_abc                        │  │
│  └────────────────────────────────────────┘  │
│  ℹ️ Lowercase, không dấu, dùng _ thay space  │
│                                              │
│  Tên hiển thị *                              │
│  ┌────────────────────────────────────────┐  │
│  │ Coffee Shop ABC                        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Mô tả                                      │
│  ┌────────────────────────────────────────┐  │
│  │ Quán cà phê specialty tại quận 1       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Icon    Màu chủ đạo                         │
│  ┌────┐  ┌────────────────────────────────┐  │
│  │ ☕ │  │ #8B4513  [🎨]                  │  │
│  └────┘  └────────────────────────────────┘  │
│                                              │
│            [Hủy]  [✅ Tạo Brand]             │
│                                              │
└──────────────────────────────────────────────┘
```

Sau khi tạo → tự động chuyển đến trang Brand Detail để bắt đầu thêm knowledge.

---

## 4. Trang Brand Detail

**URL:** `/knowledge/:brandId`

Trang này có 4 tabs:

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ← Back    ✦ TửViOnline                                        │
│            Nền tảng xem tử vi online cho Gen Z                   │
│                                                                  │
│  ┌──────────┬──────────┬───────────────┬──────────┐              │
│  │ 📄 Docs  │ 🎤 Voice │ ⚙️ Settings   │ 👁 Preview│             │
│  └──────────┴──────────┴───────────────┴──────────┘              │
│                                                                  │
│  (Tab content below)                                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Tab 1: 📄 Documents

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  📄 Documents                              [+ Thêm Document]    │
│                                                                  │
│  BRAND CORE                                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 📝 Brand Identity          1.2 KB    Edited 2h ago        │  │
│  │    identity.md                            [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 📝 Tone of Voice           2.1 KB    Edited 1d ago        │  │
│  │    tone_of_voice.md                       [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 📝 Visual Guidelines       0.8 KB    Edited 3d ago        │  │
│  │    visual_guidelines.md                   [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  PRODUCTS                                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 📦 Tử Vi Online            1.5 KB    Edited 5d ago        │  │
│  │    products/tu_vi_online.md               [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 📦 Tử Vi Premium           0.9 KB    Edited 5d ago        │  │
│  │    products/tu_vi_premium.md              [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  AUDIENCE                                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 👥 Gen Z Spiritual         1.8 KB    Edited 2d ago        │  │
│  │    audience/gen_z_spiritual.md            [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  POLICIES                                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 🛡️ Claims Policy           0.5 KB    Edited 1w ago        │  │
│  │    policies/claims_policy.md              [Sửa]  [Xóa]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Modal: Thêm Document

Khi bấm "+ Thêm Document":

```
┌──────────────────────────────────────────────┐
│  Thêm Document Mới                      [X]  │
│                                              │
│  Loại document *                             │
│  ┌────────────────────────────────────────┐  │
│  │ ▼ Chọn loại                            │  │
│  │   📝 Brand Core (identity, tone, etc.) │  │
│  │   📦 Product / Dịch vụ                 │  │
│  │   👥 Audience / Persona                │  │
│  │   🛡️ Policy / Quy định                 │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Tên document *                              │
│  ┌────────────────────────────────────────┐  │
│  │ ca_phe_signature                       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│           [Hủy]  [→ Tạo & Bắt đầu viết]     │
│                                              │
└──────────────────────────────────────────────┘
```

Sau khi tạo → mở Document Editor ngay.

### Document Editor (full page)

Khi bấm [Sửa] hoặc sau khi tạo document mới:

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ← Back to TửViOnline                                           │
│                                                                  │
│  📝 Editing: Brand Identity                     [💾 Lưu] [Hủy]  │
│  identity.md · Last saved 2 hours ago                            │
│                                                                  │
│  ┌──────────────────────┬──────────────────────┐                 │
│  │                      │                      │                 │
│  │   EDITOR             │   PREVIEW            │                 │
│  │                      │                      │                 │
│  │ # TửViOnline         │   TửViOnline         │                 │
│  │                      │                      │                 │
│  │ ## Brand Identity    │   Brand Identity     │                 │
│  │                      │                      │                 │
│  │ TửViOnline là nền    │   TửViOnline là nền  │                 │
│  │ tảng xem tử vi      │   tảng xem tử vi     │                 │
│  │ online dành cho      │   online dành cho    │                 │
│  │ Gen Z...             │   Gen Z...           │                 │
│  │                      │                      │                 │
│  │ ## Mission           │   Mission            │                 │
│  │ Giúp Gen Z hiểu     │   Giúp Gen Z hiểu    │                 │
│  │ bản thân qua...      │   bản thân qua...    │                 │
│  │                      │                      │                 │
│  └──────────────────────┴──────────────────────┘                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 💡 Gợi ý: Document này nên chứa thông tin về brand        │  │
│  │    identity, mission, vision, USP, brand values.           │  │
│  │    Xem template mẫu →                                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Features của editor:**
- Split view: editor bên trái, markdown preview bên phải
- Auto-save draft (lưu vào localStorage mỗi 30 giây)
- Nút "Lưu" gọi API `PUT /api/brands/{id}/docs/{path}`
- Gợi ý template theo loại document (xem bên dưới)

### Template gợi ý theo loại document

Khi tạo document mới, auto-fill template:

**Brand Core — identity.md:**
```markdown
# [Tên Brand]

## Brand Identity
(Mô tả brand — brand là gì, làm gì, tại sao tồn tại)

## Mission
(Sứ mệnh — 1-2 câu)

## Vision
(Tầm nhìn)

## Unique Selling Proposition (USP)
(Điều gì khiến brand khác biệt)

## Brand Values
- (Giá trị 1)
- (Giá trị 2)
- (Giá trị 3)

## Brand Personality
(Brand giống ai? Đặc điểm tính cách)
```

**Brand Core — tone_of_voice.md:**
```markdown
# Tone of Voice — [Tên Brand]

## Overall Tone
(Mô tả tone chung: casual/formal/friendly/authoritative/...)

## Do's
- (Nên viết kiểu gì)
- (Nên dùng từ gì)

## Don'ts
- (Không viết kiểu gì)
- (Không dùng từ gì)

## Preferred Words/Phrases
- (Từ ưa thích 1)
- (Từ ưa thích 2)

## Avoided Words/Phrases
- (Từ tránh 1)
- (Từ tránh 2)

## Sentence Style
- Độ dài trung bình: (ngắn/trung bình/dài)
- Perspective: (ngôi thứ mấy)

## Emoji Usage
(Nhiều/vừa/ít/không dùng. Emoji ưa thích?)

## Example Posts (Good)
(Paste 3-5 bài post mẫu thể hiện đúng tone)
```

**Product:**
```markdown
# [Tên sản phẩm/dịch vụ]

## Mô tả ngắn
(1-2 câu)

## Chi tiết
(Mô tả đầy đủ)

## Đối tượng
(Ai nên dùng)

## Lợi ích chính
- (Lợi ích 1)
- (Lợi ích 2)

## Giá
(Thông tin giá nếu có)

## Claims được phép
- (Claim 1)

## Claims KHÔNG được phép
- (Claim cấm 1)
```

**Audience:**
```markdown
# Persona: [Tên persona]

## Demographics
- Tuổi: 
- Giới tính:
- Vị trí:
- Nghề nghiệp:

## Pain Points
- (Pain point 1)
- (Pain point 2)

## Motivations
- (Motivation 1)

## Awareness Stage
(unaware / problem_aware / solution_aware / product_aware / most_aware)

## Language Style
(Họ nói chuyện như thế nào? Dùng từ gì? Tone gì?)

## Where They Hang Out
(Platform nào? Group nào? Follow ai?)
```

---

### Tab 2: 🎤 Voice Profile

Editor cho voice profile dạng form (không cần edit JSON trực tiếp):

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  🎤 Voice Profile                                    [💾 Lưu]   │
│                                                                  │
│  TONE                                                            │
│  ┌──────────────────────┬──────────────────────┐                 │
│  │ Primary Tone         │ Secondary Tone        │                │
│  │ ┌──────────────────┐ │ ┌──────────────────┐  │                │
│  │ │ casual-spiritual ▼│ │ │ empathetic      ▼│  │                │
│  │ └──────────────────┘ │ └──────────────────┘  │                │
│  └──────────────────────┴──────────────────────┘                 │
│                                                                  │
│  Formality                                                       │
│  Casual ●────────○─────────────────── Formal                     │
│         0.3                                                      │
│                                                                  │
│  WRITING STYLE                                                   │
│  ┌──────────────────────┬──────────────────────┐                 │
│  │ Avg sentence length  │ Perspective           │                │
│  │ ┌──────────────────┐ │ ┌──────────────────┐  │                │
│  │ │ 15              ▲│ │ │ first_person    ▼│  │                │
│  │ └──────────────────┘ │ └──────────────────┘  │                │
│  └──────────────────────┴──────────────────────┘                 │
│                                                                  │
│  VOCABULARY                                                      │
│  Preferred words (1 per line):       Avoided words (1 per line): │
│  ┌──────────────────────┐           ┌──────────────────────┐     │
│  │ khám phá bản thân    │           │ click ngay            │     │
│  │ hành trình           │           │ mua liền              │     │
│  │ bản mệnh             │           │ ưu đãi sốc            │     │
│  │ năng lượng            │           │ chỉ còn X ngày        │     │
│  └──────────────────────┘           └──────────────────────┘     │
│                                                                  │
│  Emoji style: ┌─────────────────┐                                │
│               │ moderate       ▼│                                │
│               └─────────────────┘                                │
│  Common emojis: ┌──────────────────────────┐                     │
│                 │ ✨ 🌙 💫 🔮 🌿            │                    │
│                 └──────────────────────────┘                     │
│                                                                  │
│  ANTI-AI RULES                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Never start with 'Bạn đã bao giờ'                    [x]  │  │
│  │ Avoid 'Trong thế giới hiện đại'                       [x]  │  │
│  │ Avoid 'Không chỉ vậy', 'Hơn thế nữa'                 [x]  │  │
│  │ Never end with 'Hãy bắt đầu hành trình'              [x]  │  │
│  │ ┌──────────────────────────────────────────────────────┐   │  │
│  │ │ + Thêm rule mới...                                  │   │  │
│  │ └──────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Tab 3: ⚙️ Settings

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ⚙️ Brand Settings                                   [💾 Lưu]   │
│                                                                  │
│  GENERAL                                                         │
│  Tên hiển thị         Icon     Màu chủ đạo                       │
│  ┌──────────────────┐ ┌────┐  ┌──────────────┐                   │
│  │ TửViOnline       │ │ ✦  │  │ #6c5ce7 [🎨] │                  │
│  └──────────────────┘ └────┘  └──────────────┘                   │
│                                                                  │
│  Mô tả                                                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Nền tảng xem tử vi online cho Gen Z                       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  DEFAULT CAMPAIGN SETTINGS                                       │
│  Default channels:   ┌─────────────────────────────────────┐     │
│                      │ ☑ Facebook  ☑ Instagram  ☐ TikTok   │     │
│                      └─────────────────────────────────────┘     │
│  Default goal:       ┌──────────────────┐                        │
│                      │ awareness       ▼│                        │
│                      └──────────────────┘                        │
│                                                                  │
│  CONTENT RULES                                                   │
│  Forbidden claims (AI sẽ KHÔNG BAO GIỜ nói những điều này):      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ cam kết kết quả chắc chắn                            [x]  │  │
│  │ tiên tri tương lai                                    [x]  │  │
│  │ + Thêm claim...                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Mandatory terms (PHẢI xuất hiện trong mọi content):             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ (trống — chưa có)                                          │  │
│  │ + Thêm term...                                             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  DANGER ZONE                                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 🗑️ Xóa brand này                                          │  │
│  │ Xóa toàn bộ knowledge của brand. Không thể hoàn tác.      │  │
│  │                                      [Xóa Brand]          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Tab 4: 👁 Preview

Preview tất cả knowledge đã có, giúp user hình dung AI sẽ "biết" gì về brand:

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  👁 Knowledge Preview                                            │
│  Đây là tất cả thông tin AI sẽ dùng khi tạo content cho brand   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ BRAND IDENTITY                                    1.2 KB  │  │
│  │ TửViOnline là nền tảng xem tử vi online dành cho Gen Z... │  │
│  │ Mission: Giúp Gen Z hiểu bản thân qua tử vi...            │  │
│  │ USP: Cá nhân hóa theo ngày giờ sinh chính xác...          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ TONE OF VOICE                                     2.1 KB  │  │
│  │ Overall: casual-spiritual, nhẹ nhàng, gần gũi...          │  │
│  │ Do's: viết như trò chuyện, dùng storytelling...            │  │
│  │ Don'ts: không giảng dạo, không tạo sợ hãi...              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ PRODUCTS (2)                                      2.4 KB  │  │
│  │ • Tử Vi Online: dịch vụ xem tử vi miễn phí...             │  │
│  │ • Tử Vi Premium: dịch vụ premium, phân tích sâu...        │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ AUDIENCE (1)                                      1.8 KB  │  │
│  │ • Gen Z Spiritual: 18-25 tuổi, quan tâm tâm linh...       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ VOICE PROFILE                                              │  │
│  │ Tone: casual-spiritual + empathetic                        │  │
│  │ Formality: 0.3 (casual)                                    │  │
│  │ Preferred: khám phá, hành trình, bản mệnh                 │  │
│  │ Avoided: click ngay, mua liền, ưu đãi sốc                 │  │
│  │ Emoji: ✨ 🌙 💫                                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Total knowledge size: 8.3 KB (~2,800 tokens)                    │
│  ℹ️ Context window usage: ~3% (tốt — dưới 10% là optimal)       │  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Phần cuối hiện **token estimate** — giúp user biết knowledge có quá lớn không (quá 15K tokens sẽ ảnh hưởng quality).

---

## 5. User Flow: Thêm brand mới từ đầu

Step-by-step flow khi user muốn thêm brand mới:

```
1. Vào "📚 Knowledge Base"
2. Bấm "+ Tạo Brand Mới"
3. Nhập: ID = "nail_spa", Name = "Nail Spa Sunny", Description = "Tiệm nail tại quận 7"
4. Bấm "Tạo"
   → Hệ thống tạo folder brands/nail_spa/ với template files
   → Chuyển đến trang Brand Detail

5. Tab "📄 Docs" — thấy 2 template files (identity.md, tone_of_voice.md) đã được tạo sẵn
6. Bấm "Sửa" identity.md → Editor mở ra với template
7. Fill content: "Nail Spa Sunny là tiệm nail cao cấp tại quận 7, chuyên nail art Hàn Quốc..."
8. Bấm "Lưu"

9. Bấm "+ Thêm Document" → chọn "Product" → tên "gel_nails"
10. Viết: "Dịch vụ sơn gel cao cấp, 200+ mẫu, giá từ 150k-500k..."
11. Bấm "Lưu"

12. Bấm "+ Thêm Document" → chọn "Audience" → tên "nu_van_phong"
13. Viết: "Nữ văn phòng 25-35 tuổi, quan tâm aesthetic, chịu chi cho ngoại hình..."
14. Bấm "Lưu"

15. Tab "🎤 Voice" → set tone = "friendly-trendy", emoji style = "high", etc.
16. Tab "⚙️ Settings" → thêm forbidden claim "đẹp nhất Sài Gòn"
17. Tab "👁 Preview" → kiểm tra tổng thể knowledge

18. Quay lại Campaign → chọn brand "💅 Nail Spa Sunny" → nhập brief → generate
    → Pipeline load đúng knowledge của Nail Spa Sunny
```

---

## 6. User Flow: Update knowledge cho brand đã có

```
1. Vào "📚 Knowledge Base"
2. Bấm "Mở" brand "TửViOnline"
3. Tab "📄 Docs"
4. Bấm "Sửa" trên "tone_of_voice.md"
5. Chỉnh: thêm preferred word "lá số", xóa avoided word cũ
6. Bấm "Lưu"
   → File updated, next campaign run sẽ dùng tone mới
```

---

## 7. React Components cần tạo

```
web/src/
├── pages/
│   ├── BrandsPage.jsx              # Brand list + create modal
│   ├── BrandDetailPage.jsx         # Tabs container
│   └── DocumentEditorPage.jsx      # Full-page markdown editor
├── components/
│   ├── brands/
│   │   ├── BrandCard.jsx           # Brand card in list
│   │   ├── CreateBrandModal.jsx    # Create brand form
│   │   ├── DocumentList.jsx        # Grouped document list
│   │   ├── DocumentEditor.jsx      # Split markdown editor + preview
│   │   ├── VoiceProfileForm.jsx    # Voice profile form editor
│   │   ├── BrandSettings.jsx       # Settings tab content
│   │   ├── KnowledgePreview.jsx    # Preview tab content
│   │   └── CompletenessBar.jsx     # Completeness indicator
│   └── shared/
│       ├── MarkdownEditor.jsx      # Textarea + preview component
│       ├── TagInput.jsx            # Reusable tag/chip input
│       └── ConfirmModal.jsx        # Confirm delete modal
```

---

## 8. API endpoints needed (summary)

```
GET    /api/brands/                          # List brands
POST   /api/brands/                          # Create brand
GET    /api/brands/:id                       # Get brand + docs list
PUT    /api/brands/:id                       # Update brand metadata
DELETE /api/brands/:id                       # Delete brand

GET    /api/brands/:id/docs/:path            # Get document content
PUT    /api/brands/:id/docs/:path            # Save document
DELETE /api/brands/:id/docs/:path            # Delete document

GET    /api/brands/:id/voice-profile         # Get voice profile
PUT    /api/brands/:id/voice-profile         # Update voice profile

GET    /api/brands/:id/preview               # Get full knowledge preview + token count
```

---

## 9. Implementation Order

1. Backend: `brand_manager.py` + API routes (đã có trong prompt trước)
2. Frontend: `BrandsPage.jsx` — list + create modal
3. Frontend: `BrandDetailPage.jsx` — tabs container
4. Frontend: `DocumentList.jsx` + `DocumentEditor.jsx`
5. Frontend: `VoiceProfileForm.jsx`
6. Frontend: `BrandSettings.jsx`
7. Frontend: `KnowledgePreview.jsx`
8. Frontend: `DocumentEditorPage.jsx` — full page editor with split view
9. Connect: brand selector trong InputPage (đã có trong prompt trước)
10. Test: full flow tạo brand → thêm docs → tạo campaign
