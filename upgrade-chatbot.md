# Marketing Agent — Upgrade: Từ "Chatbot bọc prompt" thành Marketing Operating System

## Vấn đề gốc

Agent hiện tại về bản chất vẫn là:
1. User nhập text → AI parse → AI viết strategy → AI viết content → AI review → output
2. Mỗi run là INDEPENDENT — không nhớ gì từ run trước
3. User vẫn phải nghĩ "viết gì" mỗi lần

Một chatbot (Claude/ChatGPT) + file đính kèm + prompt tốt có thể cho output tương đương.

## Agent PHẢI hơn chatbot ở đâu?

Chatbot giỏi ở: 1 task, 1 lần, với input đầy đủ từ user.
Agent phải giỏi ở: **lặp lại nhiều lần, nhất quán, tự cải thiện, giảm effort về 0**.

Dưới đây là 7 upgrades cụ thể biến agent từ "chatbot wrapper" thành tool mà chatbot không thể thay thế.

---

## Upgrade 1: Campaign Templates — "1 click, không cần nghĩ"

### Vấn đề
Mỗi lần tạo campaign, user vẫn phải nghĩ: "viết gì bây giờ?". Chatbot cũng vậy. Cả hai đều cần input từ user.

### Giải pháp
Tạo hệ thống **Campaign Templates** — user chỉ cần chọn template, agent tự fill brief.

### Implementation

**Thêm file `knowledge_base/brands/{brand_id}/templates/`:**

```
templates/
├── weekly_tips.json
├── product_launch.json
├── testimonial.json
├── behind_the_scenes.json
├── seasonal_promo.json
└── educational_series.json
```

**Mỗi template là một pre-filled CampaignBrief:**

```json
// templates/weekly_tips.json
{
  "template_id": "weekly_tips",
  "name": "Tips Hàng Tuần",
  "description": "Chia sẻ 1 tip/insight hữu ích liên quan đến brand",
  "icon": "💡",
  "brief_template": {
    "goal": "engagement",
    "channels": ["facebook", "instagram"],
    "deliverables": ["post", "carousel"],
    "key_message_template": "Chia sẻ tip về {topic}",
    "cta_template": "Save bài này để áp dụng nhé!",
    "constraints": {
      "word_limit": 250
    }
  },
  "required_input": ["topic"],
  "example_topics": [
    "cách đọc cung Mệnh",
    "ý nghĩa sao Thái Dương",
    "tử vi và career choice"
  ]
}
```

**UI — InputPage thêm template selector:**

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Brand: ✦ TửViOnline                                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ 📌 Chọn Template (hoặc viết tự do bên dưới)                │ │
│  │                                                             │ │
│  │ 💡 Tips Hàng Tuần    📦 Ra Mắt Sản Phẩm   💬 Testimonial  │ │
│  │ 🎬 Behind the Scenes ☀️ Seasonal Promo     📚 Educational  │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Đã chọn: 💡 Tips Hàng Tuần                                     │
│                                                                  │
│  Topic: ┌──────────────────────────────────────────────────┐     │
│         │ cách đọc cung Mệnh                               │     │
│         └──────────────────────────────────────────────────┘     │
│  Gợi ý: cách đọc cung Mệnh · ý nghĩa sao Thái Dương · ...     │
│                                                                  │
│  [🚀 Generate]                                                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Chatbot không làm được điều này** vì không có template system. Mỗi lần user phải viết lại prompt từ đầu.

---

## Upgrade 2: Content Calendar — "Batch cả tuần/tháng"

### Vấn đề
Chatbot = 1 lần 1 output. Marketer cần content cho CẢ TUẦN hoặc CẢ THÁNG.

### Giải pháp
Tạo **Content Calendar Generator** — user chọn brand + khoảng thời gian → agent tự tạo posting schedule + content cho từng ngày.

### Implementation

**API endpoint mới:**

```python
@router.post("/{brand_id}/calendar")
def generate_calendar(brand_id: str, req: CalendarRequest):
    """
    Generate content calendar cho 1 tuần hoặc 1 tháng.
    
    Input:
      - brand_id
      - duration: "week" | "month"
      - posts_per_week: 3-7
      - channels: ["facebook", "instagram"]
      - content_mix: {"tips": 2, "storytelling": 1, "promo": 1}
    
    Output:
      - List of campaign briefs, 1 per posting day
      - Mỗi brief có ngày đăng, template type, topic gợi ý
    """
```

**Calendar request model:**

```python
class CalendarRequest(BaseModel):
    duration: str = "week"  # "week" | "month"
    posts_per_week: int = 3
    channels: list[str] = ["facebook", "instagram"]
    content_mix: dict[str, int] = {
        "tips": 2,
        "storytelling": 1, 
        "product_highlight": 1,
    }
    start_date: Optional[str] = None  # ISO date, default = today
```

**Cách hoạt động:**

```
1. User chọn brand "TửViOnline"
2. Bấm "📅 Tạo Calendar"
3. Chọn: tuần này, 4 posts/tuần, mix = 2 tips + 1 storytelling + 1 promo
4. Agent tự:
   a. Generate 4 topics phù hợp (dựa trên brand knowledge + trends)
   b. Assign template type cho mỗi ngày
   c. Generate content cho từng post
   d. Output: calendar view với content sẵn sàng đăng
```

**UI — Calendar View:**

```
┌──────────────────────────────────────────────────────────────────┐
│  📅 Content Calendar — TửViOnline — Tuần 21/04 - 27/04         │
│                                                                  │
│  Mon 21    Wed 23    Fri 25     Sun 27                           │
│  ┌──────┐ ┌──────┐  ┌──────┐  ┌──────┐                         │
│  │💡 Tip│ │💡 Tip│  │🎬 BTS│  │📦 Pro│                         │
│  │      │ │      │  │      │  │      │                         │
│  │Cung  │ │Sao   │  │Hậu   │  │Premium│                        │
│  │Mệnh  │ │Thái  │  │trường│  │launch │                        │
│  │      │ │Dương │  │      │  │      │                         │
│  │ ✅   │ │ ✅   │  │ ⏳   │  │ ⏳   │                         │
│  └──────┘ └──────┘  └──────┘  └──────┘                         │
│                                                                  │
│  ✅ = content ready   ⏳ = pending review                        │
│                                                                  │
│  [📥 Export All]  [📋 Copy to Clipboard]                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Chatbot không thể** tạo calendar có logic scheduling, auto-assign templates, batch generate rồi cho review từng cái.

---

## Upgrade 3: Learning Memory — "Agent tốt lên theo thời gian"

### Vấn đề
Chatbot bắt đầu từ 0 mỗi conversation. Agent hiện tại cũng vậy — mỗi run là independent.

### Giải pháp
Thêm **Learning Memory** — agent nhớ feedback từ user qua các run trước, tự cải thiện.

### Implementation

**Thêm file `knowledge_base/brands/{brand_id}/memory.json`:**

```json
{
  "brand_id": "tuvionline",
  "learned_preferences": [
    {
      "type": "hook_style",
      "lesson": "User thích hook dạng câu hỏi nội tâm hơn là stat/số liệu",
      "learned_from": "run_6a1ab373",
      "date": "2026-04-18"
    },
    {
      "type": "cta_style",
      "lesson": "CTA 'miễn phí để bắt đầu' perform tốt hơn 'đặt lịch ngay'",
      "learned_from": "run_8b2cd491",
      "date": "2026-04-19"
    },
    {
      "type": "tone_adjustment",
      "lesson": "User reject strategy quá formal — cần casual hơn mặc dù tone guide nói 'professional'",
      "learned_from": "run_3f4de782",
      "date": "2026-04-20"
    },
    {
      "type": "content_pattern",
      "lesson": "Carousel slide 1 nên là câu hỏi, không phải statement",
      "learned_from": "run_9e5fg123",
      "date": "2026-04-21"
    }
  ],
  "rejected_patterns": [
    "Mở bài bằng 'Bạn có biết...'",
    "CTA dùng 'Click ngay'",
    "Carousel nhiều hơn 7 slides"
  ],
  "approved_examples": [
    {
      "run_id": "6a1ab373",
      "type": "facebook_post",
      "hook": "Có những thứ mình cảm nhận về bản thân từ lâu — nhưng chưa bao giờ có từ để nói ra.",
      "score": 0.88
    }
  ]
}
```

**Cách thu thập memory tự động:**

```python
# Trong pipeline, sau mỗi review gate:

def save_learning(brand_id: str, state: dict, user_action: str):
    """
    Tự động lưu learning từ user actions.
    
    Triggers:
    - User REJECT strategy → lưu lý do reject vào rejected_patterns
    - User EDIT content trực tiếp → so sánh original vs edited, lưu preference
    - User APPROVE → lưu hook/CTA/format vào approved_examples
    - User feedback checkboxes → lưu vào learned_preferences
    """
```

**Inject memory vào prompt:**

Khi generate content, load memory.json và inject vào prompt:

```markdown
## Lessons Learned (từ các campaign trước)
- User thích hook dạng câu hỏi nội tâm
- CTA "miễn phí để bắt đầu" tốt hơn "đặt lịch ngay"
- Carousel slide 1 nên là câu hỏi

## Patterns đã bị reject
- Không mở bài bằng "Bạn có biết..."
- Không dùng CTA "Click ngay"

## Approved examples (reference)
- Hook tốt: "Có những thứ mình cảm nhận về bản thân từ lâu..."
```

**Chatbot không có khả năng này** — mỗi conversation bắt đầu từ 0. Agent của bạn sẽ TỐT HƠN sau mỗi lần dùng.

---

## Upgrade 4: A/B Variants — "Tạo nhiều version, test xem cái nào tốt"

### Vấn đề
Chatbot cho 1 output. Muốn version khác phải hỏi lại. Agent hiện tại cũng cho 1 output.

### Giải pháp
Mỗi content piece, agent tạo **2-3 variants** với approach khác nhau.

### Implementation

Sửa `channel_renderer` — với mỗi piece, generate 2 variants:

```python
# Variant A: emotional approach
# Variant B: rational approach  
# (hoặc: hook A vs hook B, CTA A vs CTA B)
```

**Sửa ContentPiece model:**

```python
class ContentVariant(BaseModel):
    variant_label: str  # "A: Emotional Hook" / "B: Question Hook"
    body: str
    hook: Optional[str] = None
    cta_text: str = ""

class ContentPiece(BaseModel):
    channel: Channel
    deliverable: Deliverable
    variants: list[ContentVariant]  # 2-3 variants
    selected_variant: int = 0       # user chọn variant nào
    # ... rest unchanged
```

**UI — Content Review có variant toggle:**

```
┌──────────────────────────────────────────────────────────────────┐
│  FACEBOOK — Post                                                 │
│                                                                  │
│  Variant: [A: Emotional ✓]  [B: Question]  [C: Story]           │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Có những thứ mình cảm nhận về bản thân từ lâu —           │  │
│  │ nhưng chưa bao giờ có từ để nói ra...                     │  │
│  │                                                            │  │
│  │ (rest of content)                                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [✅ Chọn variant này]                                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

User chọn variant nào → approved_examples trong memory ghi nhận → lần sau agent biết prefer variant style nào.

---

## Upgrade 5: Quick Regenerate — "Không thích? 1 click làm lại"

### Vấn đề
Chatbot: không thích output → phải viết lại prompt, giải thích cần gì khác.
Agent hiện tại: phải quay lại, viết feedback, chờ re-generate.

### Giải pháp
Thêm **Quick Actions** trên mỗi content piece:

```
┌────────────────────────────────────────────────────────────────┐
│  FACEBOOK — Post                                               │
│                                                                │
│  (content hiện tại)                                            │
│                                                                │
│  Quick Actions:                                                │
│  [🔄 Viết lại]  [📝 Đổi hook]  [🎭 Đổi tone]  [✂️ Ngắn hơn]  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Mỗi quick action = 1 LLM call nhỏ với instruction cụ thể:
- "Viết lại" → re-generate cùng MasterMessage, khác approach
- "Đổi hook" → chỉ re-generate hook, giữ body
- "Đổi tone" → rewrite cùng content nhưng tone khác (casual ↔ professional)
- "Ngắn hơn" → condense xuống 70% word count

**API endpoint:**

```python
@router.post("/{run_id}/quick-action")
def quick_action(run_id: str, action: QuickActionRequest):
    """
    Quick regenerate a specific part of a content piece.
    
    Actions: "rewrite", "change_hook", "change_tone", "shorter", "longer"
    """
```

**Chatbot cần nguyên prompt mới** cho mỗi thay đổi nhỏ. Agent chỉ cần 1 click.

---

## Upgrade 6: Brand Consistency Score — "Đo được, không đoán"

### Vấn đề
Chatbot: output "có vẻ" đúng brand, nhưng không ai đo. Agent có reviewer nhưng score tự LLM cho (dễ bias).

### Giải pháp
Thêm **Brand Consistency Dashboard** — track consistency across campaigns.

**Thêm vào brand detail page:**

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 Brand Consistency — TửViOnline                               │
│  Dựa trên 12 campaigns gần nhất                                 │
│                                                                  │
│  Overall Score: 8.4/10                                           │
│                                                                  │
│  Brand Fit     ████████░░ 0.84  (stable)                         │
│  Factuality    █████████░ 0.91  (improving ↑)                    │
│  Channel Fit   ███████░░░ 0.76  (needs work)                     │
│  Business Fit  ████████░░ 0.85  (stable)                         │
│                                                                  │
│  Common Issues:                                                  │
│  • Instagram captions thường quá dài (3/12 campaigns)            │
│  • TikTok hook thỉnh thoảng quá formal (2/12)                   │
│                                                                  │
│  Top Performing Content:                                         │
│  • "Có những thứ mình cảm nhận..." — FB post, score 0.92        │
│  • "Tử vi không đoán tương lai..." — IG carousel, score 0.88    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

Dữ liệu lấy từ `review_result` của mỗi run, aggregate theo brand.

---

## Upgrade 7: Export Integrations — "Từ generate đến publish"

### Vấn đề
Chatbot: copy output → paste vào tool khác → format lại.
Agent hiện tại: download markdown → vẫn phải copy/paste.

### Giải pháp
Thêm **1-click export** sang các tool thật:

```
Export Options:
├── 📋 Copy to Clipboard (per piece — đã có)
├── 📥 Download MD / JSON / PPTX (đã có)
├── 📅 Export to Google Calendar (tạo events với content)
├── 📝 Export to Google Docs (formatted doc)
├── 📊 Export to Notion (tạo page per campaign)
└── 🔗 Export to Buffer/Hootsuite (schedule posts)
```

Phase 1 chỉ cần: Copy to Clipboard cải tiến + Download. Các integration khác = Phase 3.

**Copy to Clipboard cải tiến:**

```
┌────────────────────────────────────────────────────────────────┐
│  📋 Copy Content                                               │
│                                                                │
│  [Copy FB Post]     — copy body + hashtags                     │
│  [Copy IG Caption]  — copy caption + hashtags (30 cái)         │
│  [Copy IG Slides]   — copy slide-by-slide format               │
│  [Copy Reels Script]— copy script + visual cues                │
│  [Copy All]         — copy mọi thứ, formatted                  │
│                                                                │
│  Mỗi nút copy đúng format platform:                            │
│  - FB: body text thuần, hashtags cuối                           │
│  - IG: caption + 1 dòng trống + hashtags block                  │
│  - TikTok: script format + hashtags riêng                       │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Tổng hợp: So sánh Agent vs Chatbot sau upgrade

| Tiêu chí | Chatbot + File | Agent (hiện tại) | Agent (sau upgrade) |
|---|---|---|---|
| Tạo 1 post | ✅ Tốt | ✅ Tốt | ✅ Tốt |
| Brand consistency | ⚠️ Phụ thuộc prompt | ⚠️ Có reviewer nhưng 1 lần | ✅ Track across campaigns |
| Tạo content cả tuần | ❌ Phải hỏi 7 lần | ❌ Phải chạy 7 lần | ✅ 1 click calendar |
| Nhớ preference | ❌ Mỗi chat mới = 0 | ❌ Mỗi run = 0 | ✅ Learning memory |
| A/B testing | ❌ Hỏi thêm prompt | ❌ Không có | ✅ Auto 2-3 variants |
| Quick edit | ⚠️ Viết prompt mới | ⚠️ Feedback loop dài | ✅ 1-click actions |
| Đo consistency | ❌ Không | ⚠️ 1 run only | ✅ Dashboard across runs |
| Effort per campaign | 🔴 Cao (prompt + files) | 🟡 Trung bình (input + review) | 🟢 Thấp (chọn template + 1 click) |
| Lần thứ 50 | 🔴 Vẫn mệt như lần 1 | 🟡 Vẫn phải nhập input | 🟢 Agent đã học, nhanh hơn |

---

## Implementation Priority

### Nên làm ngay (high impact, low effort):
1. **Campaign Templates** — giảm effort nhập input về gần 0
2. **Quick Regenerate actions** — "đổi hook", "ngắn hơn" 1 click
3. **Smart Copy to Clipboard** — format đúng per platform

### Nên làm tiếp (high impact, medium effort):
4. **Learning Memory** — agent tốt lên sau mỗi run
5. **A/B Variants** — auto generate 2 options

### Phase 3 (high impact, high effort):
6. **Content Calendar** — batch generate cả tuần
7. **Brand Consistency Dashboard** — track quality over time
8. **Export integrations** — Notion, Google Docs, Buffer

---

## Cách implement: Thêm vào prompt files nào?

Tất cả upgrades trên không thay đổi kiến trúc cơ bản. Chỉ cần:

1. **Templates**: thêm `templates/` folder trong brand + API endpoint + UI selector
2. **Quick Actions**: thêm 1 API endpoint + modify channel_renderer để accept "instruction" param
3. **Learning Memory**: thêm `memory.json` per brand + inject vào prompts + save logic sau mỗi review gate
4. **A/B Variants**: modify ContentPiece model + channel_renderer prompt + UI toggle
5. **Calendar**: thêm 1 API endpoint + new CalendarPage.jsx
6. **Dashboard**: aggregate review scores từ past runs + new DashboardPage.jsx
7. **Copy Clipboard**: frontend-only, format text per platform
