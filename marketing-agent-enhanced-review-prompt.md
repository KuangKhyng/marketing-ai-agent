# Marketing Agent — Enhanced Review Flow for Web UI

## Overview

Cải thiện flow review trên web UI. Thay vì chỉ Approve/Reject đơn giản, user sẽ:
1. **Preview** output tại mỗi bước quan trọng
2. **Comment** cụ thể vào từng phần
3. **Request changes** với feedback chi tiết → agent tự sửa
4. **Approve** khi hài lòng → pipeline tiếp tục

## Flow tổng quan

```
Input → Parse Brief → [REVIEW BRIEF] → Build Context → Generate Strategy
    → [REVIEW STRATEGY] → Build Message → Render Content
    → [REVIEW CONTENT] → Final Review Scores → [APPROVE OUTPUT]
```

Có 4 điểm review (gates), mỗi gate cho phép user xem, comment, và yêu cầu sửa.

---

## Gate 1: Review Brief (nhẹ, optional)

**Khi nào:** Sau khi Brief Parser trả về CampaignBrief.

**Mục đích:** User xác nhận AI hiểu đúng ý mình trước khi chạy tiếp.

**UI:**
```python
# Hiển thị brief dạng editable form
st.subheader("📋 Parsed Brief — Kiểm tra lại")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Mục tiêu:** {brief.goal.value}")
    st.markdown(f"**Sản phẩm:** {brief.offer.product_or_service}")
    st.markdown(f"**Đối tượng:** {brief.audience.persona_description}")
    st.markdown(f"**Channels:** {', '.join(c.value for c in brief.channels)}")

with col2:
    st.markdown(f"**Key Message:** {brief.offer.key_message}")
    st.markdown(f"**CTA:** {brief.offer.cta}")
    st.markdown(f"**Awareness Stage:** {brief.audience.awareness_stage.value}")

# Editable fields — user có thể chỉnh trực tiếp
with st.expander("✏️ Chỉnh sửa brief", expanded=False):
    edited_goal = st.selectbox("Mục tiêu", ["awareness", "engagement", "lead_generation", "conversion"],
                               index=["awareness", "engagement", "lead_generation", "conversion"].index(brief.goal.value))
    edited_product = st.text_input("Sản phẩm/Dịch vụ", brief.offer.product_or_service)
    edited_audience = st.text_input("Đối tượng", brief.audience.persona_description)
    edited_channels = st.multiselect("Channels", ["facebook", "instagram", "tiktok"],
                                     default=[c.value for c in brief.channels])
    edited_key_message = st.text_input("Key Message", brief.offer.key_message)
    edited_cta = st.text_input("CTA", brief.offer.cta)

    # Nếu user chỉnh, update brief object trước khi tiếp
    if st.button("💾 Cập nhật brief"):
        # Rebuild CampaignBrief with edited values
        # Update state
        st.success("Brief đã cập nhật!")

# Quick approve — không cần mở expander nếu brief đúng
st.button("✅ Brief đúng rồi, tiếp tục →", type="primary")
```

**Behavior:**
- Mặc định auto-continue (brief thường đúng 90% cases)
- User CHỈ cần interact nếu brief sai
- Có expander để chỉnh nếu cần

---

## Gate 2: Review Strategy (quan trọng nhất)

**Khi nào:** Sau khi Strategist trả về strategy.

**Mục đích:** User review chiến lược trước khi tạo content. Đây là gate quan trọng nhất vì strategy quyết định toàn bộ direction.

**UI:**
```python
st.subheader("📋 Campaign Strategy")

# Hiển thị strategy trong card đẹp
st.markdown(strategy_text)

# === COMMENT SECTION ===
st.divider()
st.markdown("### 💬 Comments & Feedback")

# Predefined feedback options (checkboxes) — giúp user nhanh hơn
st.markdown("**Chọn nhanh vấn đề cần sửa (nếu có):**")

col1, col2 = st.columns(2)
with col1:
    fb_tone = st.checkbox("Tone chưa phù hợp")
    fb_angle = st.checkbox("Góc tiếp cận chưa đúng")
    fb_audience = st.checkbox("Chưa hiểu đúng audience")
with col2:
    fb_hook = st.checkbox("Hook chưa đủ mạnh")
    fb_cta = st.checkbox("CTA chưa rõ ràng")
    fb_platform = st.checkbox("Platform approach chưa đúng")

# Free-form comment
comment = st.text_area(
    "Ghi chú thêm (tùy chọn)",
    placeholder="Ví dụ: Tone nên casual hơn, bớt formal. Hook nên dùng câu hỏi thay vì statement. CTA nên mềm hơn, kiểu mời gọi...",
    height=100,
)

# === ACTION BUTTONS ===
col1, col2 = st.columns(2)
with col1:
    approve_btn = st.button("✅ Approve — Tiếp tục tạo content", type="primary", use_container_width=True)
with col2:
    revise_btn = st.button("🔄 Yêu cầu sửa strategy", use_container_width=True)

if revise_btn:
    # Compile feedback
    feedback_parts = []
    if fb_tone: feedback_parts.append("Tone chưa phù hợp — cần điều chỉnh")
    if fb_angle: feedback_parts.append("Góc tiếp cận chưa đúng — cần thay đổi angle")
    if fb_audience: feedback_parts.append("Chưa hiểu đúng audience — cần rethink target")
    if fb_hook: feedback_parts.append("Hook chưa đủ mạnh — cần hook gây tò mò hơn")
    if fb_cta: feedback_parts.append("CTA chưa rõ ràng — cần CTA actionable hơn")
    if fb_platform: feedback_parts.append("Platform approach chưa đúng — cần điều chỉnh per-platform")
    if comment:
        feedback_parts.append(f"Ghi chú từ user: {comment}")

    feedback_text = "\n".join(f"- {fb}" for fb in feedback_parts)

    # Re-run strategist with feedback
    st.session_state.strategy_feedback = feedback_text
    st.session_state.strategy_revision_count += 1
    # → trigger strategist re-run (xem Pipeline Integration bên dưới)

if approve_btn:
    st.session_state.phase = "generating_content"
    st.rerun()
```

**Pipeline Integration — Strategist re-run with feedback:**

```python
# Trong src/web/pipeline.py

def rerun_strategist(state: dict, feedback: str) -> dict:
    """Re-run strategist node with user feedback injected into prompt."""

    # Append feedback to the user message
    # Strategist node cần được modify để nhận feedback
    state["strategy_feedback"] = feedback
    state.update(strategist_node(state))
    return state
```

**Modify `src/nodes/strategist.py`** — thêm handling cho feedback:

```python
def strategist_node(state: dict) -> dict:
    # ... existing code ...

    # Build user message
    user_parts = [
        f"## Campaign Brief\n```json\n{brief.model_dump_json(indent=2)}\n```",
        f"## Brand Context\n{context_pack.get('brand', 'N/A')}",
        # ... other parts ...
    ]

    # === NEW: Inject user feedback if this is a revision ===
    strategy_feedback = state.get("strategy_feedback")
    if strategy_feedback:
        user_parts.append(
            f"## ⚠️ USER FEEDBACK — BẮT BUỘC PHẢI SỬA\n"
            f"User đã review strategy trước đó và yêu cầu sửa:\n\n"
            f"{strategy_feedback}\n\n"
            f"Hãy viết lại strategy MỚI HOÀN TOÀN, address tất cả feedback trên."
        )

    # ... rest of node ...
```

---

## Gate 3: Review Content (chi tiết nhất)

**Khi nào:** Sau khi Channel Renderer trả về content cho tất cả platforms.

**Mục đích:** User review từng piece content, comment vào từng piece cụ thể, yêu cầu sửa piece nào cần sửa.

**UI:**
```python
st.subheader("✍️ Generated Content — Review")

# Tabs theo platform
content_pieces = st.session_state.pipeline_state["campaign_content"].pieces
tabs = st.tabs([f"{p.channel.value.upper()} — {p.deliverable.value}" for p in content_pieces])

# Track feedback per piece
if "piece_feedback" not in st.session_state:
    st.session_state.piece_feedback = {}

for i, (tab, piece) in enumerate(zip(tabs, content_pieces)):
    with tab:
        piece_key = f"{piece.channel.value}_{piece.deliverable.value}"

        # === CONTENT DISPLAY ===
        # Hook
        if piece.hook:
            st.markdown(f"**🪝 Hook:** {piece.hook}")

        # Body — hiển thị trong editable text area
        st.markdown("**📝 Content:**")

        # Toggle: view mode vs edit mode
        edit_mode = st.toggle("Chỉnh sửa trực tiếp", key=f"edit_{piece_key}")

        if edit_mode:
            edited_body = st.text_area(
                "Nội dung",
                value=piece.body,
                height=300,
                key=f"body_{piece_key}",
            )
            if edited_body != piece.body:
                # User đã edit — save edit
                piece.body = edited_body
                st.success("Đã lưu chỉnh sửa!")
        else:
            st.markdown(piece.body)

        # CTA
        if piece.cta_text:
            st.success(f"**CTA:** {piece.cta_text}")

        # Hashtags
        if piece.hashtags:
            st.caption(" ".join(piece.hashtags))

        # Visual direction (collapsible)
        if piece.visual_direction:
            with st.expander("🎨 Visual Direction"):
                st.markdown(piece.visual_direction)

        # Word count
        st.caption(f"Word count: {piece.word_count}")

        # === FEEDBACK PER PIECE ===
        st.divider()
        st.markdown(f"**💬 Feedback cho {piece.channel.value} — {piece.deliverable.value}:**")

        # Quick feedback checkboxes
        col1, col2 = st.columns(2)
        with col1:
            fb_ok = st.checkbox("✅ Content này OK", key=f"ok_{piece_key}", value=True)
        with col2:
            fb_needs_change = st.checkbox("🔄 Cần sửa", key=f"change_{piece_key}")

        if fb_needs_change:
            piece_comment = st.text_area(
                "Cần sửa gì?",
                placeholder="Ví dụ: Hook chưa đủ mạnh, body quá dài, tone quá formal...",
                key=f"comment_{piece_key}",
                height=80,
            )
            st.session_state.piece_feedback[piece_key] = {
                "needs_change": True,
                "comment": piece_comment,
                "channel": piece.channel.value,
                "deliverable": piece.deliverable.value,
            }
        else:
            st.session_state.piece_feedback.pop(piece_key, None)

# === OVERALL ACTIONS ===
st.divider()

# Summary of feedback
pieces_needing_change = [v for v in st.session_state.piece_feedback.values() if v.get("needs_change")]

if pieces_needing_change:
    st.warning(f"⚠️ {len(pieces_needing_change)} piece(s) cần sửa")
    for fb in pieces_needing_change:
        st.markdown(f"- **{fb['channel']}/{fb['deliverable']}**: {fb.get('comment', 'Chưa có comment')}")

# Action buttons
col1, col2 = st.columns(2)
with col1:
    approve_content = st.button(
        "✅ Approve tất cả — Chạy final review",
        type="primary",
        use_container_width=True,
        disabled=len(pieces_needing_change) > 0,  # Disable nếu còn piece cần sửa
    )
with col2:
    revise_content = st.button(
        f"🔄 Yêu cầu sửa {len(pieces_needing_change)} piece(s)",
        use_container_width=True,
        disabled=len(pieces_needing_change) == 0,
    )

if revise_content:
    # Compile feedback cho revision
    revision_feedback = compile_content_feedback(st.session_state.piece_feedback)
    # Re-run message_architect + channel_renderer with feedback
    # (xem Pipeline Integration bên dưới)

if approve_content:
    st.session_state.phase = "final_review"
    st.rerun()
```

**Pipeline Integration — Content revision with per-piece feedback:**

```python
# Trong src/web/pipeline.py

def compile_content_feedback(piece_feedback: dict) -> str:
    """Compile per-piece feedback into revision instructions."""
    parts = ["User đã review content và yêu cầu sửa các piece sau:\n"]
    for key, fb in piece_feedback.items():
        if fb.get("needs_change"):
            parts.append(f"- [{fb['channel']}/{fb['deliverable']}]: {fb.get('comment', 'Cần sửa')}")
    parts.append("\nChỉ sửa các piece được yêu cầu. Giữ nguyên các piece đã OK.")
    return "\n".join(parts)


def revise_content(state: dict, feedback: str) -> dict:
    """Re-run content generation with user feedback."""
    # Inject feedback into review_result so message_architect picks it up
    from src.models.review import ReviewResult, DimensionScore, ReviewDimension

    # Create a synthetic review result with user feedback
    state["review_result"] = ReviewResult(
        overall_passed=False,
        dimension_scores=[
            DimensionScore(dimension=d, score=0.5, passed=False, feedback="User requested revision")
            for d in ReviewDimension
        ],
        revision_instructions=feedback,
        critical_issues=[feedback],
    )

    # Re-run message architect (it reads review_result.revision_instructions)
    state.update(message_architect_node(state))
    if state.get("error"):
        return state

    # Re-run channel renderer
    state.update(channel_renderer_node(state))

    return state
```

---

## Gate 4: Final Review & Approve Output

**Khi nào:** Sau khi Reviewer node chạy xong (auto review scores).

**Mục đích:** User xem review scores, quyết định approve output cuối cùng hay yêu cầu sửa thêm.

**UI:**
```python
st.subheader("📊 Final Review")

# Review scores
score_cols = st.columns(4)
for i, score in enumerate(review_result.dimension_scores):
    with score_cols[i]:
        st.metric(
            label=score.dimension.value.replace("_", " ").title(),
            value=f"{score.score:.2f}",
            delta="PASS" if score.passed else "FAIL",
            delta_color="normal" if score.passed else "inverse",
        )
        # Show feedback in tooltip/expander
        with st.expander("Chi tiết"):
            st.caption(score.feedback)

overall = "✅ PASSED" if review_result.overall_passed else "❌ FAILED"
st.markdown(f"### Overall: {overall}")

# If failed, show what needs fixing
if not review_result.overall_passed:
    st.error("Content chưa đạt tiêu chuẩn. Xem chi tiết bên dưới.")
    if review_result.revision_instructions:
        st.markdown(review_result.revision_instructions)

# === FINAL ACTION ===
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    final_approve = st.button("✅ Approve & Export", type="primary", use_container_width=True)
with col2:
    go_back = st.button("← Quay lại chỉnh content", use_container_width=True)
with col3:
    restart = st.button("🔄 Làm lại từ đầu", use_container_width=True)

if final_approve:
    # Run formatter → save output → show download buttons
    st.session_state.phase = "export"
    st.rerun()

if go_back:
    st.session_state.phase = "review_content"
    st.rerun()

if restart:
    # Reset all session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
```

---

## Session State Full Schema

```python
# Tất cả session state keys cần quản lý

st.session_state = {
    # Phase control
    "phase": "input",  # "input" | "review_brief" | "review_strategy" | "review_content" | "final_review" | "export"

    # Pipeline state
    "pipeline_state": None,  # CampaignState dict

    # Review feedback
    "strategy_feedback": None,  # str — feedback cho strategy revision
    "strategy_revision_count": 0,  # int — số lần sửa strategy
    "piece_feedback": {},  # dict — per-piece feedback
    "content_revision_count": 0,  # int — số lần sửa content

    # History
    "history": [],  # list of past run summaries
}
```

---

## Pipeline Flow — Complete với all gates

```python
# src/web/pipeline.py

class PipelineRunner:
    """Manages the multi-gate pipeline execution."""

    def __init__(self):
        self.state = None

    def phase_1_parse(self, campaign_input: str) -> dict:
        """Parse brief + build context. Returns state for brief review."""
        self.state = self._init_state(campaign_input)
        self.state.update(brief_parser_node(self.state))
        if self.state.get("error"):
            return self.state
        self.state.update(context_builder_node(self.state))
        return self.state

    def phase_2_strategy(self, feedback: str = None) -> dict:
        """Generate strategy. Accepts optional feedback for revision."""
        if feedback:
            self.state["strategy_feedback"] = feedback
        self.state.update(strategist_node(self.state))
        return self.state

    def phase_3_content(self, feedback: str = None) -> dict:
        """Generate content. Accepts optional feedback for revision."""
        if feedback:
            # Inject as revision instructions
            self._inject_revision_feedback(feedback)

        self.state["human_approved"] = True
        self.state.update(message_architect_node(self.state))
        if self.state.get("error"):
            return self.state

        self.state.update(channel_renderer_node(self.state))
        return self.state

    def phase_4_review(self) -> dict:
        """Run automated review."""
        self.state.update(reviewer_node(self.state))
        return self.state

    def phase_5_export(self) -> dict:
        """Format and save final output."""
        self.state.update(formatter_node(self.state))
        return self.state

    def update_brief(self, updated_brief) -> None:
        """Update brief after user edits in Gate 1."""
        self.state["brief"] = updated_brief
        # Re-run context builder with updated brief
        self.state.update(context_builder_node(self.state))

    def update_content_piece(self, piece_index: int, new_body: str) -> None:
        """Update a specific content piece after user inline edit."""
        pieces = self.state["campaign_content"].pieces
        if 0 <= piece_index < len(pieces):
            pieces[piece_index].body = new_body
            pieces[piece_index].word_count = len(new_body.split())

    def _init_state(self, campaign_input: str) -> dict:
        return {
            "raw_input": campaign_input,
            "brief": None,
            "context_pack": None,
            "strategy": None,
            "strategy_feedback": None,
            "human_approved": False,
            "master_message": None,
            "campaign_content": None,
            "review_result": None,
            "revision_count": 0,
            "max_revisions": 2,
            "trace": RunTrace(),
            "current_node": "",
            "error": None,
        }

    def _inject_revision_feedback(self, feedback: str) -> None:
        from src.models.review import ReviewResult, DimensionScore, ReviewDimension
        self.state["review_result"] = ReviewResult(
            overall_passed=False,
            dimension_scores=[
                DimensionScore(dimension=d, score=0.5, passed=False, feedback="User revision")
                for d in ReviewDimension
            ],
            revision_instructions=feedback,
            critical_issues=[],
        )
```

---

## web.py — Main App Structure

```python
import streamlit as st
from src.web.pipeline import PipelineRunner

st.set_page_config(page_title="Marketing Agent", page_icon="🎯", layout="wide")

# Initialize
if "phase" not in st.session_state:
    st.session_state.phase = "input"
    st.session_state.runner = PipelineRunner()

runner = st.session_state.runner

# === SIDEBAR (always visible) ===
with st.sidebar:
    st.title("🎯 Marketing Agent")
    st.caption("AI-powered social media campaign generator")

    # Show current phase
    phases = ["input", "review_brief", "review_strategy", "review_content", "final_review", "export"]
    current_idx = phases.index(st.session_state.phase) if st.session_state.phase in phases else 0

    for i, phase in enumerate(phases):
        icon = "✅" if i < current_idx else ("▶️" if i == current_idx else "⬜")
        label = phase.replace("_", " ").title()
        st.caption(f"{icon} {label}")

    st.divider()

    # Reset button (always available)
    if st.button("🔄 New Campaign"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# === MAIN AREA — route by phase ===
if st.session_state.phase == "input":
    render_input_phase()

elif st.session_state.phase == "review_brief":
    render_brief_review()

elif st.session_state.phase == "review_strategy":
    render_strategy_review()

elif st.session_state.phase == "review_content":
    render_content_review()

elif st.session_state.phase == "final_review":
    render_final_review()

elif st.session_state.phase == "export":
    render_export()
```

---

## State modification cần thêm vào CampaignState

Thêm field `strategy_feedback` vào `src/graph/state.py`:

```python
class CampaignState(TypedDict):
    # ... existing fields ...
    strategy_feedback: Optional[str]  # NEW: feedback từ user cho strategy revision
```

Và modify `strategist_node` để đọc field này (xem Gate 2 section ở trên).

---

## Giới hạn revision

Để tránh loop vô hạn:

```python
MAX_STRATEGY_REVISIONS = 3
MAX_CONTENT_REVISIONS = 2

# Trong render_strategy_review():
if st.session_state.strategy_revision_count >= MAX_STRATEGY_REVISIONS:
    st.warning(f"Đã sửa strategy {MAX_STRATEGY_REVISIONS} lần. Vui lòng approve hoặc bắt đầu lại.")
    # Disable revise button
```

---

## Implementation Order

1. Tạo `src/web/__init__.py` + `src/web/pipeline.py` (PipelineRunner class)
2. Tạo `web.py` — main app với phase routing
3. Implement `render_input_phase()` — input form
4. Implement `render_brief_review()` — Gate 1 (simple, auto-continue option)
5. Implement `render_strategy_review()` — Gate 2 (comment + feedback checkboxes)
6. Implement `render_content_review()` — Gate 3 (per-piece review, inline edit)
7. Implement `render_final_review()` — Gate 4 (scores + final approve)
8. Implement `render_export()` — download buttons
9. Modify `strategist_node` để nhận `strategy_feedback`
10. Thêm `strategy_feedback` vào `CampaignState`
11. Test full flow
12. Styling (.streamlit/config.toml)
