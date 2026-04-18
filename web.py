"""
Marketing Agent — Web UI (Streamlit)
Run: streamlit run web.py
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Marketing Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.web.pipeline import PipelineRunner, compile_content_feedback, MAX_STRATEGY_REVISIONS, MAX_CONTENT_REVISIONS
from src.models.brief import CampaignBrief, CampaignGoal, BrandSpec, AudienceSpec, OfferSpec, Channel, Deliverable, AwarenessStage

OUTPUTS_DIR = Path(__file__).resolve().parent / "outputs"


# ── Session State Init ──────────────────────────────────────────────

def init_session():
    defaults = {
        "phase": "input",
        "runner": PipelineRunner(),
        "strategy_revision_count": 0,
        "content_revision_count": 0,
        "piece_feedback": {},
        "history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()
runner: PipelineRunner = st.session_state.runner


# ── Sidebar ──────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.title("🎯 Marketing Agent")
        st.caption("AI-powered campaign generator")

        st.divider()

        # Phase progress indicator
        phases = [
            ("input", "📝 Input"),
            ("review_brief", "📋 Brief Review"),
            ("review_strategy", "🧠 Strategy Review"),
            ("review_content", "✍️ Content Review"),
            ("final_review", "📊 Final Review"),
            ("export", "📦 Export"),
        ]
        current_phase = st.session_state.phase
        phase_names = [p[0] for p in phases]
        current_idx = phase_names.index(current_phase) if current_phase in phase_names else 0

        for i, (_, label) in enumerate(phases):
            if i < current_idx:
                st.markdown(f"✅ ~~{label}~~")
            elif i == current_idx:
                st.markdown(f"▶️ **{label}**")
            else:
                st.markdown(f"⬜ {label}")

        st.divider()

        # Reset button
        if st.button("🔄 New Campaign", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # History
        st.divider()
        st.subheader("📜 History")
        _render_history()


def _render_history():
    """Show past runs from outputs/ directory."""
    if not OUTPUTS_DIR.exists():
        st.caption("No past runs yet")
        return

    runs = sorted(OUTPUTS_DIR.iterdir(), reverse=True)
    if not runs:
        st.caption("No past runs yet")
        return

    for run_dir in runs[:10]:  # last 10
        if not run_dir.is_dir():
            continue
        trace_file = run_dir / "trace.json"
        if trace_file.exists():
            try:
                trace = json.loads(trace_file.read_text(encoding="utf-8"))
                summary = trace.get("brief_summary", run_dir.name)
                cost = trace.get("total_cost_estimate", 0)
                st.caption(f"📁 `{run_dir.name}` — {summary[:40]} (${cost:.3f})")
            except Exception:
                st.caption(f"📁 `{run_dir.name}`")


# ── Phase: Input ─────────────────────────────────────────────────────

def render_input_phase():
    st.header("📝 Campaign Brief")
    st.markdown("Nhập yêu cầu campaign — AI sẽ phân tích và tạo content cho bạn.")

    input_mode = st.radio(
        "Input mode",
        ["Free text", "Structured form"],
        horizontal=True,
    )

    if input_mode == "Free text":
        campaign_input = st.text_area(
            "Mô tả campaign",
            placeholder="Ví dụ: Tạo campaign awareness cho dịch vụ tử vi online, target Gen Z quan tâm tâm linh. Channels: Facebook và Instagram.",
            height=150,
        )
    else:
        col1, col2 = st.columns(2)
        with col1:
            goal = st.selectbox("Mục tiêu", ["awareness", "engagement", "lead_generation", "conversion"])
            product = st.text_input("Sản phẩm/Dịch vụ", placeholder="Dịch vụ xem tử vi online")
            audience = st.text_input("Đối tượng", placeholder="Gen Z quan tâm tâm linh")
        with col2:
            channels = st.multiselect("Channels", ["facebook", "instagram", "tiktok"], default=["facebook", "instagram"])
            key_message = st.text_input("Thông điệp chính", placeholder="Khám phá bản thân qua lá số tử vi")
            cta = st.text_input("CTA", placeholder="Đặt lịch xem tử vi")

        campaign_input = f"Tạo campaign {goal} cho {product}, target {audience}. Channels: {', '.join(channels)}. Key message: {key_message}. CTA: {cta}"

    st.divider()

    if st.button("🚀 Generate Campaign", type="primary", use_container_width=True, disabled=not campaign_input):
        with st.status("🔍 Phân tích brief & thu thập context...", expanded=True) as status:
            st.write("Parsing campaign brief...")
            state = runner.phase_1_parse(campaign_input)

            if state.get("error"):
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {state['error']}")
                return

            st.write("✅ Brief parsed successfully")
            st.write("✅ Context assembled from knowledge base")
            status.update(label="✅ Brief & Context ready", state="complete")

        st.session_state.phase = "review_brief"
        st.rerun()


# ── Phase: Review Brief (Gate 1) ────────────────────────────────────

def render_brief_review():
    state = runner.state
    brief = state.get("brief")

    if not brief:
        st.error("No brief found. Please go back to input.")
        return

    st.header("📋 Parsed Brief — Kiểm tra lại")
    st.markdown("AI đã phân tích yêu cầu của bạn thành brief dưới đây. Xem có đúng ý không.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🎯 Mục tiêu:** `{brief.goal.value}`")
        st.markdown(f"**📦 Sản phẩm:** {brief.offer.product_or_service}")
        st.markdown(f"**👥 Đối tượng:** {brief.audience.persona_description}")

    with col2:
        st.markdown(f"**📱 Channels:** {', '.join(c.value for c in brief.channels)}")
        st.markdown(f"**💬 Key Message:** {brief.offer.key_message}")
        st.markdown(f"**🔗 CTA:** {brief.offer.cta}")
        st.markdown(f"**🧠 Awareness Stage:** `{brief.audience.awareness_stage.value}`")

    # Editable brief section
    with st.expander("✏️ Chỉnh sửa brief", expanded=False):
        goals = ["awareness", "engagement", "lead_generation", "conversion"]
        edited_goal = st.selectbox(
            "Mục tiêu", goals,
            index=goals.index(brief.goal.value) if brief.goal.value in goals else 0,
        )
        edited_product = st.text_input("Sản phẩm/Dịch vụ", brief.offer.product_or_service)
        edited_audience = st.text_input("Đối tượng", brief.audience.persona_description)
        edited_channels = st.multiselect(
            "Channels", ["facebook", "instagram", "tiktok"],
            default=[c.value for c in brief.channels],
        )
        edited_key_message = st.text_input("Key Message", brief.offer.key_message)
        edited_cta = st.text_input("CTA", brief.offer.cta)

        if st.button("💾 Cập nhật brief"):
            # Rebuild brief with edited values
            brief.goal = CampaignGoal(edited_goal)
            brief.offer.product_or_service = edited_product
            brief.offer.key_message = edited_key_message
            brief.offer.cta = edited_cta
            brief.audience.persona_description = edited_audience
            brief.channels = [Channel(c) for c in edited_channels]

            # Update deliverables based on new channels
            deliverables = set()
            for ch in brief.channels:
                if ch == Channel.FACEBOOK:
                    deliverables.add(Deliverable.POST)
                elif ch == Channel.INSTAGRAM:
                    deliverables.update([Deliverable.CAROUSEL, Deliverable.REELS_SCRIPT])
                elif ch == Channel.TIKTOK:
                    deliverables.add(Deliverable.SHORT_VIDEO_SCRIPT)
            brief.deliverables = list(deliverables)

            runner.update_brief(brief)
            st.success("Brief đã cập nhật!")

    st.divider()

    if st.button("✅ Brief đúng rồi, tiếp tục →", type="primary", use_container_width=True):
        with st.status("🧠 Đang tạo chiến lược campaign...", expanded=True) as status:
            st.write("Generating strategy with Claude Sonnet...")
            runner.phase_2_strategy()

            if runner.state.get("error"):
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {runner.state['error']}")
                return

            st.write("✅ Strategy generated!")
            status.update(label="✅ Strategy ready", state="complete")

        st.session_state.phase = "review_strategy"
        st.rerun()


# ── Phase: Review Strategy (Gate 2) ─────────────────────────────────

def render_strategy_review():
    state = runner.state
    strategy = state.get("strategy", "")

    if not strategy:
        st.error("No strategy found.")
        return

    st.header("🧠 Campaign Strategy")

    revision_count = st.session_state.strategy_revision_count
    if revision_count > 0:
        st.info(f"Revision #{revision_count} / {MAX_STRATEGY_REVISIONS}")

    st.markdown(strategy)

    # Feedback section
    st.divider()
    st.subheader("💬 Feedback")

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

    comment = st.text_area(
        "Ghi chú thêm (tùy chọn)",
        placeholder="Ví dụ: Tone nên casual hơn, bớt formal. Hook nên dùng câu hỏi thay vì statement...",
        height=100,
    )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        approve_btn = st.button("✅ Approve — Tạo content", type="primary", use_container_width=True)
    with col2:
        can_revise = revision_count < MAX_STRATEGY_REVISIONS
        revise_btn = st.button(
            f"🔄 Yêu cầu sửa strategy",
            use_container_width=True,
            disabled=not can_revise,
        )
        if not can_revise:
            st.caption(f"Đã đạt giới hạn {MAX_STRATEGY_REVISIONS} lần sửa.")

    if approve_btn:
        with st.status("✍️ Đang tạo content...", expanded=True) as status:
            st.write("Building message architecture...")
            runner.phase_3_content()

            if runner.state.get("error"):
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {runner.state['error']}")
                return

            pieces_count = len(runner.state["campaign_content"].pieces)
            st.write(f"✅ {pieces_count} content pieces generated!")
            status.update(label="✅ Content generated", state="complete")

        st.session_state.phase = "review_content"
        st.rerun()

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

        if not feedback_parts:
            st.warning("Vui lòng chọn ít nhất 1 vấn đề hoặc ghi chú trước khi yêu cầu sửa.")
            return

        feedback_text = "\n".join(f"- {fb}" for fb in feedback_parts)

        with st.status("🔄 Đang sửa strategy...", expanded=True) as status:
            st.write(f"Revision #{revision_count + 1}...")
            runner.phase_2_strategy(feedback=feedback_text)

            if runner.state.get("error"):
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {runner.state['error']}")
                return

            st.write("✅ Strategy revised!")
            status.update(label="✅ Strategy updated", state="complete")

        st.session_state.strategy_revision_count += 1
        st.rerun()


# ── Phase: Review Content (Gate 3) ──────────────────────────────────

def render_content_review():
    state = runner.state
    content = state.get("campaign_content")

    if not content:
        st.error("No content found.")
        return

    revision_count = st.session_state.content_revision_count

    st.header("✍️ Generated Content — Review")
    if revision_count > 0:
        st.info(f"Content revision #{revision_count} / {MAX_CONTENT_REVISIONS}")

    pieces = content.pieces

    # Tabs per piece
    tab_labels = [f"{p.channel.value.upper()} — {p.deliverable.value.replace('_', ' ').title()}" for p in pieces]
    tabs = st.tabs(tab_labels)

    if "piece_feedback" not in st.session_state:
        st.session_state.piece_feedback = {}

    for i, (tab, piece) in enumerate(zip(tabs, pieces)):
        with tab:
            piece_key = f"{piece.channel.value}_{piece.deliverable.value}"

            # Header row
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                st.markdown(f"### {piece.deliverable.value.replace('_', ' ').title()}")
            with col_h2:
                st.metric("Words", piece.word_count)

            # Hook
            if piece.hook:
                st.markdown(f"**🪝 Hook:** {piece.hook}")

            # Body — toggle view/edit
            edit_mode = st.toggle("✏️ Chỉnh sửa trực tiếp", key=f"edit_{piece_key}")

            if edit_mode:
                edited_body = st.text_area(
                    "Nội dung",
                    value=piece.body,
                    height=300,
                    key=f"body_{piece_key}",
                )
                if edited_body != piece.body:
                    runner.update_content_piece(i, edited_body)
                    st.success("Đã lưu chỉnh sửa!")
            else:
                st.markdown(piece.body)

            # CTA
            if piece.cta_text:
                st.success(f"**CTA:** {piece.cta_text}")

            # Hashtags
            if piece.hashtags:
                st.caption(" ".join(piece.hashtags))

            # Collapsible sections
            if piece.visual_direction:
                with st.expander("🎨 Visual Direction"):
                    st.markdown(piece.visual_direction)

            if piece.notes:
                with st.expander("📝 Notes"):
                    st.markdown(piece.notes)

            # Per-piece feedback
            st.divider()
            st.markdown(f"**💬 Feedback:**")

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                fb_ok = st.checkbox("✅ OK", key=f"ok_{piece_key}", value=True)
            with col_f2:
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

    # Overall actions
    st.divider()

    pieces_needing_change = [v for v in st.session_state.piece_feedback.values() if v.get("needs_change")]

    if pieces_needing_change:
        st.warning(f"⚠️ {len(pieces_needing_change)} piece(s) cần sửa")
        for fb in pieces_needing_change:
            st.markdown(f"- **{fb['channel']}/{fb['deliverable']}**: {fb.get('comment', 'Chưa có comment')}")

    col1, col2 = st.columns(2)
    with col1:
        approve_content = st.button(
            "✅ Approve — Chạy final review",
            type="primary",
            use_container_width=True,
        )
    with col2:
        can_revise = revision_count < MAX_CONTENT_REVISIONS
        revise_content = st.button(
            f"🔄 Yêu cầu sửa ({len(pieces_needing_change)} piece)",
            use_container_width=True,
            disabled=not can_revise or len(pieces_needing_change) == 0,
        )
        if not can_revise:
            st.caption(f"Đã đạt giới hạn {MAX_CONTENT_REVISIONS} lần sửa content.")

    if approve_content:
        with st.status("📊 Đang review content...", expanded=True) as status:
            st.write("Running automated review (brand, factuality, channel, business)...")
            runner.phase_4_review()

            if runner.state.get("error"):
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {runner.state['error']}")
                return

            st.write("✅ Review complete!")
            status.update(label="✅ Review complete", state="complete")

        st.session_state.phase = "final_review"
        st.rerun()

    if revise_content and pieces_needing_change:
        feedback_text = compile_content_feedback(st.session_state.piece_feedback)

        with st.status("🔄 Đang sửa content...", expanded=True) as status:
            st.write(f"Content revision #{revision_count + 1}...")
            runner.phase_3_content(feedback=feedback_text)

            if runner.state.get("error"):
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {runner.state['error']}")
                return

            st.write("✅ Content revised!")
            status.update(label="✅ Content updated", state="complete")

        st.session_state.content_revision_count += 1
        st.session_state.piece_feedback = {}
        st.rerun()


# ── Phase: Final Review (Gate 4) ────────────────────────────────────

def render_final_review():
    state = runner.state
    review_result = state.get("review_result")
    content = state.get("campaign_content")

    if not review_result:
        st.error("No review result found.")
        return

    st.header("📊 Final Review")

    # Score cards
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
            with st.expander("Chi tiết"):
                st.caption(score.feedback)

    overall = "✅ PASSED" if review_result.overall_passed else "❌ FAILED"
    st.markdown(f"### Overall: {overall}")

    if not review_result.overall_passed:
        st.error("Content chưa đạt tiêu chuẩn.")
        if review_result.revision_instructions:
            with st.expander("📋 Revision instructions"):
                st.markdown(review_result.revision_instructions)

    # Content preview
    st.divider()
    st.subheader("📄 Content Preview")
    _render_content_preview(content)

    # Actions
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        final_approve = st.button("✅ Approve & Export", type="primary", use_container_width=True)
    with col2:
        go_back = st.button("← Quay lại chỉnh content", use_container_width=True)
    with col3:
        restart = st.button("🔄 Làm lại từ đầu", use_container_width=True)

    if final_approve:
        with st.status("📦 Exporting...", expanded=True) as status:
            st.write("Formatting and saving output...")
            runner.phase_5_export()
            st.write("✅ Output saved!")
            status.update(label="✅ Export complete", state="complete")

        st.session_state.phase = "export"
        st.rerun()

    if go_back:
        st.session_state.phase = "review_content"
        st.rerun()

    if restart:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def _render_content_preview(content):
    """Render content pieces in tabs."""
    if not content:
        return

    tab_labels = [f"{p.channel.value.upper()} — {p.deliverable.value.replace('_', ' ').title()}" for p in content.pieces]
    tabs = st.tabs(tab_labels)

    for tab, piece in zip(tabs, content.pieces):
        with tab:
            if piece.hook:
                st.markdown(f"**🪝 Hook:** {piece.hook}")
            st.markdown(piece.body)
            if piece.cta_text:
                st.success(f"**CTA:** {piece.cta_text}")
            if piece.hashtags:
                st.caption(" ".join(piece.hashtags))


# ── Phase: Export ────────────────────────────────────────────────────

def render_export():
    state = runner.state
    content = state.get("campaign_content")
    trace = state.get("trace")

    st.header("🎉 Campaign Complete!")

    # Success banner
    st.balloons()

    # Run info
    if trace:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Run ID", trace.run_id)
        with col2:
            st.metric("Content Pieces", len(content.pieces) if content else 0)
        with col3:
            st.metric("Estimated Cost", f"${trace.total_cost_estimate:.4f}")

    # Content display
    if content:
        st.divider()
        st.subheader("📄 Final Content")
        _render_content_preview(content)

    # Download buttons
    st.divider()
    st.subheader("📥 Download")

    run_id = trace.run_id if trace else "unknown"
    run_dir = OUTPUTS_DIR / run_id

    col1, col2 = st.columns(2)
    with col1:
        if run_dir.exists() and (run_dir / "content.md").exists():
            md_content = (run_dir / "content.md").read_text(encoding="utf-8")
            st.download_button(
                "📥 Download Markdown",
                data=md_content,
                file_name=f"campaign_{run_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        else:
            st.button("📥 Download Markdown", disabled=True, use_container_width=True)

    with col2:
        if run_dir.exists() and (run_dir / "content.json").exists():
            json_content = (run_dir / "content.json").read_text(encoding="utf-8")
            st.download_button(
                "📥 Download JSON",
                data=json_content,
                file_name=f"campaign_{run_id}.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.button("📥 Download JSON", disabled=True, use_container_width=True)

    # New campaign button
    st.divider()
    if st.button("🚀 New Campaign", type="primary", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ── Main Router ──────────────────────────────────────────────────────

render_sidebar()

phase = st.session_state.phase

if phase == "input":
    render_input_phase()
elif phase == "review_brief":
    render_brief_review()
elif phase == "review_strategy":
    render_strategy_review()
elif phase == "review_content":
    render_content_review()
elif phase == "final_review":
    render_final_review()
elif phase == "export":
    render_export()
