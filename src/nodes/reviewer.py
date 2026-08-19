"""
Reviewer Node
- Input: CampaignContent + CampaignBrief + context_pack + MasterMessage
- Output: ReviewResult (Pydantic model)
- Model: Claude Haiku (checking task) + rule-based checks
- Type: Semi-deterministic

Scores content on 5 dimensions:
1. Brand fit (threshold: 0.7)
2. Factuality (threshold: 0.9)
3. Channel fit (threshold: 0.6)
4. Business fit (threshold: 0.7)
5. Content depth (threshold: 0.7)
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.review import (
    DimensionScore,
    LLMReviewOutput,
    ReviewDimension,
    ReviewResult,
)
from src.knowledge.untrusted import UNTRUSTED_DATA_NOTICE
from src.models.trace import NodeTrace
from src.config.settings import get_api_key, get_model_config, get_platform_specs
from src.utils.trace import update_trace
from src.utils.callbacks import TokenUsageHandler, estimate_tokens

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "reviewer.md"

# Pass thresholds per dimension
THRESHOLDS = {
    ReviewDimension.BRAND_FIT: 0.7,
    ReviewDimension.FACTUALITY: 0.9,
    ReviewDimension.CHANNEL_FIT: 0.6,
    ReviewDimension.BUSINESS_FIT: 0.7,
    ReviewDimension.CONTENT_DEPTH: 0.7,    # NEW
}


def _load_prompt() -> str:
    # Knowledge đi thẳng vào prompt này — xem src/knowledge/untrusted.py
    return PROMPT_PATH.read_text(encoding="utf-8") + UNTRUSTED_DATA_NOTICE


def reviewer_node(state: dict) -> dict:
    """
    Review campaign content across 5 dimensions.

    Kết hợp rule check (bằng code) với đánh giá của LLM. Chiều nào vi phạm
    quy tắc cứng thì KHÔNG ĐẠT, bất kể LLM chấm bao nhiêu.

    Reviewer lỗi => overall_passed=False + review_unavailable=True. Fail-closed:
    "chưa kiểm được" không được phép hiện ra như "đã đạt".

    Args:
        state: CampaignState dict with 'campaign_content', 'brief',
               'context_pack', 'master_message'.

    Returns:
        Updated state with 'review_result' and updated 'revision_count'.
    """
    # Early exit if previous node errored
    if state.get("error"):
        return {"current_node": "reviewer"}

    node_trace = NodeTrace(
        node_name="reviewer",
        started_at=datetime.now(),
        input_summary=f"Reviewing {len(state['campaign_content'].pieces)} content pieces",
    )

    try:
        brief = state["brief"]
        content = state["campaign_content"]
        context_pack = state["context_pack"]
        master_message = state["master_message"]

        # Step 1: Rule-based checks
        rule_issues = _run_rule_checks(content, brief, context_pack)

        # Step 2: LLM-based evaluation
        config = get_model_config("reviewer")
        llm_review = _run_llm_review(content, brief, context_pack, master_message, config, node_trace)

        # Step 3: Combine results
        review_result = _combine_results(rule_issues, llm_review)

        node_trace.output_summary = (
            f"Review: {'PASSED' if review_result.overall_passed else 'FAILED'}, "
            f"scores={{{', '.join(f'{s.dimension.value}: {s.score:.2f}' for s in review_result.dimension_scores)}}}"
        )
        node_trace.finished_at = datetime.now()

        # Update revision count
        revision_count = state.get("revision_count", 0)
        if not review_result.overall_passed:
            revision_count += 1

        return {
            "review_result": review_result,
            "revision_count": revision_count,
            "current_node": "reviewer",
            "trace": update_trace(state, node_trace),
        }

    except Exception as e:
        logger.exception("Reviewer lỗi — nội dung sẽ bị đánh dấu CHƯA kiểm được")
        node_trace.error = f"Review failed: {str(e)}"
        node_trace.finished_at = datetime.now()

        # Reviewer lỗi => KHÔNG kết luận là đạt. Cổng chất lượng fail-closed.
        fallback_review = ReviewResult(
            overall_passed=False,
            review_unavailable=True,
            dimension_scores=[
                DimensionScore(
                    dimension=dim,
                    score=0.0,
                    passed=False,
                    feedback="Chưa chấm được — reviewer gặp lỗi.",
                )
                for dim in ReviewDimension
            ],
            critical_issues=[f"Reviewer lỗi, nội dung CHƯA được kiểm: {str(e)}"],
            suggestions=["Cần người đọc lại toàn bộ nội dung trước khi dùng."],
            revision_instructions=None,
        )

        # Tăng revision_count kể cả khi lỗi: nhánh LangGraph dùng biến này để
        # chặn vòng lặp. Không tăng thì reviewer lỗi liên tục sẽ retry vô hạn.
        return {
            "review_result": fallback_review,
            "revision_count": state.get("revision_count", 0) + 1,
            "current_node": "reviewer",
            "trace": update_trace(state, node_trace),
        }



def _run_rule_checks(content, brief, context_pack) -> list[tuple[ReviewDimension, str]]:
    """
    Rule check bằng code (chạy TRƯỚC LLM). Mỗi vi phạm được gắn vào một
    dimension cụ thể để `_combine_results` biết chiều nào phải trượt.

    Đây là dữ kiện kiểm được, không phải ý kiến — nên nó thắng điểm của LLM:
      - dài/ngắn quá giới hạn                     -> channel_fit
      - thiếu từ user yêu cầu (must_include)      -> business_fit
      - chứa từ phải tránh / thiếu mandatory term -> brand_fit
      - chứa forbidden claim của brand            -> factuality
      - hashtag sai format, nội dung trùng lặp    -> channel_fit
    """
    issues: list[tuple[ReviewDimension, str]] = []

    for piece in content.pieces:
        piece_label = f"[{piece.channel.value}/{piece.deliverable.value}]"

        def add(dimension: ReviewDimension, message: str) -> None:
            issues.append((dimension, f"{piece_label} {message}"))

        # Word count check
        if brief.constraints.word_limit and piece.word_count > brief.constraints.word_limit:
            add(
                ReviewDimension.CHANNEL_FIT,
                f"Word count {piece.word_count} exceeds limit {brief.constraints.word_limit}",
            )

        # Required terms check
        body_lower = piece.body.lower()
        for term in brief.constraints.must_include:
            if term.lower() not in body_lower:
                add(ReviewDimension.BUSINESS_FIT, f"Missing required term: '{term}'")

        # Forbidden terms check
        for term in brief.constraints.must_avoid:
            if term.lower() in body_lower:
                add(ReviewDimension.BRAND_FIT, f"Contains forbidden term: '{term}'")

        # Brand forbidden claims check
        for claim in brief.brand.forbidden_claims:
            if claim.lower() in body_lower:
                add(ReviewDimension.FACTUALITY, f"Contains forbidden brand claim: '{claim}'")

        # Mandatory brand terms check
        for term in brief.brand.mandatory_terms:
            if term.lower() not in body_lower:
                add(ReviewDimension.BRAND_FIT, f"Missing mandatory brand term: '{term}'")

        # Platform-specific word count ranges
        specs = get_platform_specs(piece.channel.value, piece.deliverable.value)
        if isinstance(specs, dict):
            min_words = specs.get("min_words")
            max_words = specs.get("max_words")
            if min_words and piece.word_count < int(min_words):
                add(
                    ReviewDimension.CHANNEL_FIT,
                    f"Too short: {piece.word_count} words (min: {min_words})",
                )
            if max_words and piece.word_count > int(max_words):
                add(
                    ReviewDimension.CHANNEL_FIT,
                    f"Too long: {piece.word_count} words (max: {max_words})",
                )

        # Hashtag format check: all must be lowercase
        for hashtag in piece.hashtags:
            if hashtag != hashtag.lower():
                add(ReviewDimension.CHANNEL_FIT, f"Hashtag not lowercase: '{hashtag}'")

        # Content duplication check: headline/hook/body first line
        body_first_line = piece.body.split("\n")[0].strip() if piece.body else ""
        if piece.headline and piece.hook:
            if piece.headline.strip().lower() == piece.hook.strip().lower():
                add(ReviewDimension.CHANNEL_FIT, "Duplicate: headline = hook (same text)")
        if piece.headline and body_first_line:
            if piece.headline.strip().lower() == body_first_line.lower():
                add(ReviewDimension.CHANNEL_FIT, "Duplicate: headline = body first line")
        if piece.hook and body_first_line:
            if piece.hook.strip().lower() == body_first_line.lower():
                add(ReviewDimension.CHANNEL_FIT, "Duplicate: hook = body first line")

    return issues


def _run_llm_review(
    content, brief, context_pack, master_message, config, node_trace
) -> LLMReviewOutput:
    """LLM-based evaluation using Claude Haiku."""
    llm = ChatAnthropic(
        model=config["model"],
        temperature=config["temperature"],
        max_tokens=config["max_tokens"],
        api_key=get_api_key(),
    )

    system_prompt = _load_prompt()

    # Build review context
    content_text = "\n\n---\n\n".join(
        f"### {piece.channel.value} / {piece.deliverable.value}\n"
        f"**Headline:** {piece.headline or 'N/A'}\n"
        f"**Hook:** {piece.hook or 'N/A'}\n"
        f"**Body:**\n{piece.body}\n"
        f"**CTA:** {piece.cta_text}\n"
        f"**Hashtags:** {', '.join(piece.hashtags)}\n"
        f"**Word count:** {piece.word_count}"
        for piece in content.pieces
    )

    voice_profile = context_pack.get("voice_profile", {})

    user_parts = [
        f"## Content Pieces to Review\n{content_text}",
        f"## Original Brief\n```json\n{brief.model_dump_json(indent=2)}\n```",
        f"## Master Message\n```json\n{master_message.model_dump_json(indent=2)}\n```",
        f"## Voice Profile\n```json\n{json.dumps(voice_profile, ensure_ascii=False, indent=2)}\n```",
        f"## Product Context\n{context_pack.get('product', 'N/A')}",
        f"## Policies\n{context_pack.get('policies', 'N/A')}",
    ]

    user_message = "\n\n---\n\n".join(user_parts)

    structured_llm = llm.with_structured_output(LLMReviewOutput)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Đánh giá content theo 5 dimensions:\n\n{user_message}"),
    ]

    handler = TokenUsageHandler()
    result = structured_llm.invoke(messages, config={"callbacks": [handler]})

    node_trace.model_used = config["model"]
    if handler.has_data:
        node_trace.token_usage = handler.get_usage()
    else:
        node_trace.token_usage = {
            "input": estimate_tokens(system_prompt + user_message),
            "output": estimate_tokens(result.model_dump_json()),
        }

    return result


def _combine_results(
    rule_issues: list[tuple[ReviewDimension, str]],
    llm_review: LLMReviewOutput,
) -> ReviewResult:
    """
    Ghép rule check với điểm của LLM thành kết luận cuối.

    Ba quy tắc:
      1. Luôn trả về đủ 5 dimension. Chiều nào LLM không chấm thì tính là
         KHÔNG ĐẠT — thiếu đánh giá không được phép trôi thành "đạt".
      2. LLM trả trùng một chiều thì giữ điểm thấp nhất.
      3. Chiều nào có vi phạm quy tắc cứng thì trượt, bất kể điểm LLM.
    """
    # Điểm LLM theo chiều; trùng thì giữ điểm thấp nhất
    by_dim: dict[ReviewDimension, object] = {}
    for score in llm_review.dimension_scores:
        current = by_dim.get(score.dimension)
        if current is None or score.score < current.score:
            by_dim[score.dimension] = score

    # Vi phạm quy tắc cứng, gom theo chiều
    violations_by_dim: dict[ReviewDimension, list[str]] = {}
    for dimension, message in rule_issues:
        violations_by_dim.setdefault(dimension, []).append(message)

    dimension_scores = []
    unscored = []

    for dimension in ReviewDimension:
        violations = violations_by_dim.get(dimension, [])
        llm_score = by_dim.get(dimension)

        if llm_score is None:
            unscored.append(dimension.value)
            dimension_scores.append(DimensionScore(
                dimension=dimension,
                score=0.0,
                passed=False,
                feedback="Reviewer không trả về đánh giá cho chiều này — cần đọc lại bằng mắt.",
                rule_violations=violations,
            ))
            continue

        threshold = THRESHOLDS.get(dimension, 0.7)
        feedback = llm_score.feedback
        if violations:
            feedback = f"Vi phạm {len(violations)} quy tắc cứng. {feedback}"

        dimension_scores.append(DimensionScore(
            dimension=dimension,
            score=llm_score.score,
            passed=llm_score.score >= threshold and not violations,
            feedback=feedback,
            rule_violations=violations,
        ))

    overall_passed = all(ds.passed for ds in dimension_scores)

    critical_issues = list(llm_review.critical_issues) + [msg for _, msg in rule_issues]
    if unscored:
        logger.warning("LLM không chấm các chiều: %s", ", ".join(unscored))
        critical_issues.append("Reviewer không chấm các chiều: " + ", ".join(unscored))

    # Hướng dẫn sửa: chiều trượt kèm đúng những vi phạm của chiều đó
    revision_instructions = None
    if not overall_passed:
        parts = []
        for ds in dimension_scores:
            if ds.passed:
                continue
            parts.append(f"- {ds.dimension.value} (score: {ds.score:.2f}): {ds.feedback}")
            parts.extend(f"    · {v}" for v in ds.rule_violations)
        revision_instructions = "Hãy sửa content theo các vấn đề sau:\n" + "\n".join(parts)

    return ReviewResult(
        overall_passed=overall_passed,
        dimension_scores=dimension_scores,
        critical_issues=critical_issues,
        suggestions=llm_review.suggestions,
        revision_instructions=revision_instructions or llm_review.revision_instructions,
    )
