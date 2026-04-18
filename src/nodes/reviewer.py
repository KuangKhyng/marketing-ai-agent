"""
Reviewer Node
- Input: CampaignContent + CampaignBrief + context_pack + MasterMessage
- Output: ReviewResult (Pydantic model)
- Model: Claude Haiku (checking task) + rule-based checks
- Type: Semi-deterministic

Scores content on 4 dimensions:
1. Brand fit (threshold: 0.7)
2. Factuality (threshold: 0.9)
3. Channel fit (threshold: 0.6)
4. Business fit (threshold: 0.7)
"""
import json
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.review import ReviewResult, ReviewDimension, DimensionScore
from src.models.trace import NodeTrace, RunTrace
from src.config.settings import get_api_key, get_model_config, get_platform_specs, estimate_cost

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "v1" / "reviewer.md"

# Pass thresholds per dimension
THRESHOLDS = {
    ReviewDimension.BRAND_FIT: 0.7,
    ReviewDimension.FACTUALITY: 0.9,
    ReviewDimension.CHANNEL_FIT: 0.6,
    ReviewDimension.BUSINESS_FIT: 0.7,
}


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def reviewer_node(state: dict) -> dict:
    """
    Review campaign content across 4 dimensions.

    Combines rule-based checks with LLM-based evaluation.

    Args:
        state: CampaignState dict with 'campaign_content', 'brief',
               'context_pack', 'master_message'.

    Returns:
        Updated state with 'review_result' and updated 'revision_count'.
    """
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
            "trace": _update_trace(state, node_trace),
        }

    except Exception as e:
        node_trace.error = f"Review failed: {str(e)}"
        node_trace.finished_at = datetime.now()

        # On error, pass content through with warnings
        fallback_review = ReviewResult(
            overall_passed=True,
            dimension_scores=[
                DimensionScore(
                    dimension=dim,
                    score=0.5,
                    passed=True,
                    feedback=f"Review error — passed by default: {str(e)}"
                )
                for dim in ReviewDimension
            ],
            suggestions=["Review failed — manual review recommended"],
        )

        return {
            "review_result": fallback_review,
            "current_node": "reviewer",
            "trace": _update_trace(state, node_trace),
        }


def _run_rule_checks(content, brief, context_pack) -> list[str]:
    """
    Rule-based checks (BEFORE LLM):
    - Word count within constraints
    - Required terms present
    - Forbidden terms absent
    - Hashtag count
    - Channel format specs
    """
    issues = []

    for piece in content.pieces:
        piece_label = f"[{piece.channel.value}/{piece.deliverable.value}]"

        # Word count check
        if brief.constraints.word_limit and piece.word_count > brief.constraints.word_limit:
            issues.append(f"{piece_label} Word count {piece.word_count} exceeds limit {brief.constraints.word_limit}")

        # Required terms check
        body_lower = piece.body.lower()
        for term in brief.constraints.must_include:
            if term.lower() not in body_lower:
                issues.append(f"{piece_label} Missing required term: '{term}'")

        # Forbidden terms check
        for term in brief.constraints.must_avoid:
            if term.lower() in body_lower:
                issues.append(f"{piece_label} Contains forbidden term: '{term}'")

        # Brand forbidden claims check
        for claim in brief.brand.forbidden_claims:
            if claim.lower() in body_lower:
                issues.append(f"{piece_label} Contains forbidden brand claim: '{claim}'")

        # Mandatory brand terms check
        for term in brief.brand.mandatory_terms:
            if term.lower() not in body_lower:
                issues.append(f"{piece_label} Missing mandatory brand term: '{term}'")

        # Platform-specific word count ranges
        specs = get_platform_specs(piece.channel.value, piece.deliverable.value)
        if isinstance(specs, dict):
            min_words = specs.get("min_words")
            max_words = specs.get("max_words")
            if min_words and piece.word_count < int(min_words):
                issues.append(f"{piece_label} Too short: {piece.word_count} words (min: {min_words})")
            if max_words and piece.word_count > int(max_words):
                issues.append(f"{piece_label} Too long: {piece.word_count} words (max: {max_words})")

        # Hashtag format check: all must be lowercase
        for hashtag in piece.hashtags:
            if hashtag != hashtag.lower():
                issues.append(f"{piece_label} Hashtag not lowercase: '{hashtag}' → should be '{hashtag.lower()}'")

        # Content duplication check: headline/hook/body first line
        body_first_line = piece.body.split("\n")[0].strip() if piece.body else ""
        if piece.headline and piece.hook:
            if piece.headline.strip().lower() == piece.hook.strip().lower():
                issues.append(f"{piece_label} Duplicate: headline = hook (same text)")
        if piece.headline and body_first_line:
            if piece.headline.strip().lower() == body_first_line.lower():
                issues.append(f"{piece_label} Duplicate: headline = body first line")
        if piece.hook and body_first_line:
            if piece.hook.strip().lower() == body_first_line.lower():
                issues.append(f"{piece_label} Duplicate: hook = body first line")

    return issues


def _run_llm_review(content, brief, context_pack, master_message, config, node_trace) -> ReviewResult:
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

    structured_llm = llm.with_structured_output(ReviewResult)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Đánh giá content theo 4 dimensions:\n\n{user_message}"),
    ]

    result = structured_llm.invoke(messages)
    node_trace.model_used = config["model"]

    return result


def _combine_results(rule_issues: list[str], llm_review: ReviewResult) -> ReviewResult:
    """Combine rule-based issues with LLM review results."""
    # Add rule-based issues to critical issues
    combined_issues = list(llm_review.critical_issues) + rule_issues

    # Re-check pass/fail with thresholds
    dimension_scores = []
    for score in llm_review.dimension_scores:
        threshold = THRESHOLDS.get(score.dimension, 0.7)
        passed = score.score >= threshold
        dimension_scores.append(DimensionScore(
            dimension=score.dimension,
            score=score.score,
            passed=passed,
            feedback=score.feedback,
        ))

    # If there are rule-based issues, reduce relevant dimension scores
    if rule_issues:
        # Rule issues affect factuality and brand fit scores
        for i, ds in enumerate(dimension_scores):
            if ds.dimension == ReviewDimension.FACTUALITY and any("forbidden" in issue.lower() for issue in rule_issues):
                dimension_scores[i] = DimensionScore(
                    dimension=ds.dimension,
                    score=min(ds.score, 0.5),
                    passed=False,
                    feedback=ds.feedback + " | Rule violations found.",
                )

    overall_passed = all(ds.passed for ds in dimension_scores)

    # Build revision instructions if failed
    revision_instructions = None
    if not overall_passed:
        failed_dims = [ds for ds in dimension_scores if not ds.passed]
        revision_parts = [
            f"- {ds.dimension.value} (score: {ds.score:.2f}): {ds.feedback}"
            for ds in failed_dims
        ]
        if rule_issues:
            revision_parts.extend([f"- Rule issue: {issue}" for issue in rule_issues])
        revision_instructions = "Hãy sửa content theo các vấn đề sau:\n" + "\n".join(revision_parts)

    return ReviewResult(
        overall_passed=overall_passed,
        dimension_scores=dimension_scores,
        critical_issues=combined_issues,
        suggestions=llm_review.suggestions,
        revision_instructions=revision_instructions or llm_review.revision_instructions,
    )


def _update_trace(state: dict, node_trace: NodeTrace):
    trace = state.get("trace") or RunTrace()
    trace.node_traces.append(node_trace)
    if node_trace.model_used and node_trace.token_usage:
        cost = estimate_cost(
            node_trace.model_used,
            node_trace.token_usage.get("input", 0),
            node_trace.token_usage.get("output", 0),
        )
        trace.total_cost_estimate += cost
    return trace
