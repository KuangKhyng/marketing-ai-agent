# Marketing Agent — Web UI Implementation Prompt

## Overview

Thêm Streamlit web UI cho Marketing Agent Workflow Engine. User sẽ tương tác với agent qua browser thay vì CLI.

## Tech Stack
- **Streamlit** (đã có trong optional deps: `pip install marketing-agent[ui]`)
- Dùng `streamlit-extras` nếu cần components nâng cao
- Kết nối trực tiếp vào LangGraph workflow đã có

## Yêu cầu chức năng

### Trang chính — Campaign Generator

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  🎯 Marketing Agent                    [Settings ⚙️]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  Sidebar:                    Main Area:             │
│  ┌─────────────┐            ┌─────────────────────┐│
│  │ Campaign     │            │                     ││
│  │ Input Form   │            │  Pipeline Progress  ││
│  │              │            │  & Output Display   ││
│  │ - Text input │            │                     ││
│  │ - Goal select│            │                     ││
│  │ - Channels   │            │                     ││
│  │ - Generate   │            │                     ││
│  │              │            │                     ││
│  │ History      │            │                     ││
│  │ - Run 1      │            │                     ││
│  │ - Run 2      │            │                     ││
│  └─────────────┘            └─────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### Sidebar — Input Form

```python
with st.sidebar:
    st.title("🎯 Campaign Brief")

    # Input method: free text hoặc structured form
    input_mode = st.radio("Input mode", ["Free text", "Structured form"])

    if input_mode == "Free text":
        campaign_input = st.text_area(
            "Mô tả campaign",
            placeholder="Ví dụ: Tạo campaign awareness cho dịch vụ tử vi online, target Gen Z quan tâm tâm linh",
            height=120,
        )
    else:
        # Structured form
        goal = st.selectbox("Mục tiêu", ["awareness", "engagement", "lead_generation", "conversion"])
        product = st.text_input("Sản phẩm/Dịch vụ", "Dịch vụ xem tử vi online")
        audience = st.text_input("Đối tượng", "Gen Z quan tâm tâm linh")
        channels = st.multiselect("Channels", ["facebook", "instagram", "tiktok"], default=["facebook", "instagram"])
        key_message = st.text_input("Thông điệp chính", "Khám phá bản thân qua lá số tử vi")
        cta = st.text_input("CTA", "Đặt lịch xem tử vi")

        # Build campaign_input from structured form
        campaign_input = f"Tạo campaign {goal} cho {product}, target {audience}. Channels: {', '.join(channels)}. Key message: {key_message}. CTA: {cta}"

    generate_btn = st.button("🚀 Generate Campaign", type="primary", use_container_width=True)

    # History section
    st.divider()
    st.subheader("📜 History")
    # Load from outputs/ directory
    # Show list of past runs with timestamp + brief summary
```

### Main Area — Pipeline Progress & Output

**Flow có 4 phases, mỗi phase hiển thị progress:**

```python
if generate_btn and campaign_input:
    # Initialize session state
    st.session_state.running = True

    # Phase 1: Parse & Context
    with st.status("🔍 Phân tích brief & thu thập context...", expanded=True) as status:
        st.write("Parsing campaign brief...")
        # Run brief_parser_node
        st.write("Assembling context from knowledge base...")
        # Run context_builder_node
        status.update(label="✅ Brief & Context ready", state="complete")

    # Phase 2: Strategy (with approval)
    with st.status("📋 Tạo chiến lược campaign...", expanded=True) as status:
        st.write("Generating strategy...")
        # Run strategist_node
        status.update(label="📋 Strategy ready — cần review", state="complete")

    # Display strategy for approval
    st.subheader("📋 Campaign Strategy")
    st.markdown(strategy_text)  # Show strategy in markdown

    # Approval buttons
    col1, col2 = st.columns(2)
    with col1:
        approve_btn = st.button("✅ Approve", type="primary", use_container_width=True)
    with col2:
        reject_btn = st.button("❌ Reject", use_container_width=True)

    # If approved, continue pipeline
    if approve_btn:
        # Phase 3: Content Generation
        with st.status("✍️ Tạo content...", expanded=True) as status:
            st.write("Building message architecture...")
            # Run message_architect_node
            st.write("Rendering channel content...")
            # Run channel_renderer_node
            status.update(label="✅ Content generated", state="complete")

        # Phase 4: Review
        with st.status("🔎 Review content...", expanded=True) as status:
            st.write("Reviewing content quality...")
            # Run reviewer_node
            status.update(label="✅ Review complete", state="complete")

        # Display final output
        display_campaign_output(campaign_content, review_result)
```

### Output Display

```python
def display_campaign_output(content, review_result):
    """Display the final campaign output."""

    # Master Message card
    st.subheader("💡 Master Message")
    st.info(content.master_message_summary)

    # Content tabs — one per channel
    tabs = st.tabs([piece.channel.value.upper() for piece in content.pieces])

    for tab, piece in zip(tabs, content.pieces):
        with tab:
            # Header with deliverable type and word count
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {piece.deliverable.value.replace('_', ' ').title()}")
            with col2:
                st.metric("Words", piece.word_count)

            # Content body
            if piece.hook:
                st.markdown(f"**Hook:** {piece.hook}")
            st.markdown(piece.body)

            if piece.cta_text:
                st.success(f"**CTA:** {piece.cta_text}")

            if piece.hashtags:
                st.caption(" ".join(piece.hashtags))

            # Visual direction (collapsible)
            if piece.visual_direction:
                with st.expander("🎨 Visual Direction"):
                    st.markdown(piece.visual_direction)

            # Notes (collapsible)
            if piece.notes:
                with st.expander("📝 Notes"):
                    st.markdown(piece.notes)

            # Copy button
            st.button(f"📋 Copy {piece.channel.value} content", key=f"copy_{piece.channel.value}_{piece.deliverable.value}")

    # Review Scores
    st.divider()
    st.subheader("📊 Review Scores")

    score_cols = st.columns(4)
    for i, score in enumerate(review_result.dimension_scores):
        with score_cols[i]:
            delta_color = "normal" if score.passed else "inverse"
            st.metric(
                label=score.dimension.value.replace("_", " ").title(),
                value=f"{score.score:.2f}",
                delta="PASS" if score.passed else "FAIL",
                delta_color=delta_color,
            )

    overall = "✅ PASSED" if review_result.overall_passed else "❌ FAILED"
    st.markdown(f"**Overall: {overall}**")

    # Download buttons
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        # Download markdown
        st.download_button("📥 Download .md", data=markdown_content, file_name="campaign.md", mime="text/markdown")
    with col2:
        # Download JSON
        st.download_button("📥 Download .json", data=json_content, file_name="campaign.json", mime="application/json")
    with col3:
        # Export to PPTX (Phase 2)
        st.button("📥 Export PPTX", disabled=True)
```

## Cách kết nối với LangGraph workflow

**QUAN TRỌNG:** Không chạy workflow.stream() trực tiếp trong Streamlit vì human approval gate dùng `interrupt()` sẽ không tương thích với Streamlit's execution model.

Thay vào đó, **chạy từng node thủ công** (manual orchestration):

```python
# File: web.py (Streamlit app)

import streamlit as st
from src.nodes.brief_parser import brief_parser_node
from src.nodes.context_builder import context_builder_node
from src.nodes.strategist import strategist_node
from src.nodes.message_architect import message_architect_node
from src.nodes.channel_renderer import channel_renderer_node
from src.nodes.reviewer import reviewer_node
from src.nodes.formatter import formatter_node
from src.models.trace import RunTrace


def run_pipeline(campaign_input: str):
    """Run the pipeline step by step, yielding control for human approval."""

    # Initialize state
    state = {
        "raw_input": campaign_input,
        "brief": None,
        "context_pack": None,
        "strategy": None,
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

    # Step 1: Parse brief
    state.update(brief_parser_node(state))
    if state.get("error"):
        return state, "error"

    # Step 2: Build context
    state.update(context_builder_node(state))
    if state.get("error"):
        return state, "error"

    # Step 3: Generate strategy
    state.update(strategist_node(state))
    if state.get("error"):
        return state, "error"

    # PAUSE HERE — return state for human approval
    return state, "awaiting_approval"


def continue_pipeline(state: dict):
    """Continue pipeline after human approval."""

    # Step 4: Message architecture
    state.update(message_architect_node(state))
    if state.get("error"):
        return state, "error"

    # Step 5: Channel rendering
    state.update(channel_renderer_node(state))
    if state.get("error"):
        return state, "error"

    # Step 6: Review (with retry loop)
    for attempt in range(state["max_revisions"] + 1):
        state.update(reviewer_node(state))
        if state.get("error"):
            return state, "error"

        if state["review_result"].overall_passed:
            break

        if state["revision_count"] >= state["max_revisions"]:
            break

        # Retry: re-run message architect + channel renderer
        state.update(message_architect_node(state))
        state.update(channel_renderer_node(state))

    # Step 7: Format output
    state.update(formatter_node(state))

    return state, "completed"
```

## Streamlit Session State Management

```python
# Trong web.py

# Session state keys:
# - st.session_state.pipeline_state: dict — current CampaignState
# - st.session_state.phase: str — "input" | "strategy_review" | "generating" | "completed"
# - st.session_state.history: list — past run summaries

if "phase" not in st.session_state:
    st.session_state.phase = "input"
    st.session_state.pipeline_state = None
    st.session_state.history = []

# Phase routing
if st.session_state.phase == "input":
    # Show input form
    # On "Generate" button → run_pipeline() → set phase to "strategy_review"
    pass

elif st.session_state.phase == "strategy_review":
    # Show strategy + Approve/Reject buttons
    # On "Approve" → continue_pipeline() → set phase to "completed"
    # On "Reject" → set phase to "input"
    pass

elif st.session_state.phase == "completed":
    # Show final output
    # "New Campaign" button → reset to "input"
    pass
```

## File Structure

```
marketing-agent/
├── web.py                    # Streamlit app entry point
├── src/
│   └── web/                  # Web UI helpers (optional)
│       ├── __init__.py
│       ├── pipeline.py       # run_pipeline() + continue_pipeline()
│       ├── components.py     # Reusable Streamlit components
│       └── export.py         # Export to markdown/JSON/PPTX
```

## Run Command

```bash
# Install UI dependencies
pip install streamlit

# Run
streamlit run web.py

# Or with uv
uv run streamlit run web.py
```

## Styling

Thêm `.streamlit/config.toml` cho custom theme:

```toml
[theme]
primaryColor = "#6c5ce7"
backgroundColor = "#faf7f2"
secondaryBackgroundColor = "#f0eee9"
textColor = "#2d3748"
font = "sans serif"

[server]
headless = true
port = 8501
```

## Lưu ý quan trọng

1. **Không dùng LangGraph interrupt()** trong Streamlit — dùng manual orchestration (gọi từng node). LangGraph interrupt() chỉ hoạt động trong async streaming context, không tương thích với Streamlit's synchronous rerun model.

2. **Session state là critical** — Streamlit rerun toàn bộ script mỗi lần user interact. Tất cả state phải lưu trong `st.session_state`.

3. **LLM calls tốn thời gian** — dùng `st.status()` hoặc `st.spinner()` để show progress. Mỗi node call mất 3-10 giây.

4. **File upload (Phase 2)** — cho phép user upload brand guidelines, sample posts để override knowledge base mặc định.

5. **Cache** — dùng `@st.cache_data` cho knowledge base loading (không đổi giữa các runs).

## Implementation Order

1. Tạo `web.py` với layout cơ bản (sidebar + main)
2. Implement `src/web/pipeline.py` — manual orchestration (tách khỏi LangGraph interrupt)
3. Wire sidebar input form → pipeline
4. Implement strategy review UI (approve/reject buttons)
5. Implement output display (tabs per channel, scores)
6. Thêm download buttons (md, json)
7. Thêm history panel (load from outputs/)
8. Styling + polish
