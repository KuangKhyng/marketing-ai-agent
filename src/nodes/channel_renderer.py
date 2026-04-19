"""
Channel Renderer Node
- Input: CampaignBrief + MasterMessage + context_pack (platform rules + voice profile)
- Output: CampaignContent (list of ContentPiece)
- Model: Claude Sonnet
- Type: Agentic

Renders native content per platform. Integrates voice profile + anti-AI patterns.
"""
import json
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.brief import Channel, Deliverable
from src.models.content import ContentPiece, CampaignContent
from src.models.trace import NodeTrace
from src.config.settings import get_api_key, get_model_config
from src.utils.trace import update_trace
from src.utils.callbacks import TokenUsageHandler, estimate_tokens

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts" / "v1"

# Map channels to their default deliverables
CHANNEL_DELIVERABLES = {
    Channel.FACEBOOK: [Deliverable.POST],
    Channel.INSTAGRAM: [Deliverable.CAROUSEL, Deliverable.REELS_SCRIPT],
    Channel.TIKTOK: [Deliverable.SHORT_VIDEO_SCRIPT],
}


def _load_channel_prompt(channel: str) -> str:
    """Load channel-specific prompt template."""
    prompt_path = PROMPTS_DIR / f"channel_renderer_{channel}.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"No prompt template for channel: {channel}")


def channel_renderer_node(state: dict) -> dict:
    """
    Render native content for each platform channel.

    Iterates over brief.channels, generates ContentPiece for each
    channel+deliverable combination.

    Args:
        state: CampaignState dict with 'brief', 'master_message', 'context_pack'.

    Returns:
        Updated state with 'campaign_content' key.
    """
    # Early exit if previous node errored
    if state.get("error"):
        return {"current_node": "channel_renderer"}

    node_trace = NodeTrace(
        node_name="channel_renderer",
        started_at=datetime.now(),
        input_summary=f"Rendering for channels: {[c.value for c in state['brief'].channels]}",
    )

    config = get_model_config("channel_renderer")

    try:
        brief = state["brief"]
        master_message = state["master_message"]
        context_pack = state["context_pack"]

        all_pieces = []

        # Collect all render tasks
        render_tasks = []
        for channel in brief.channels:
            channel_deliverables = [
                d for d in brief.deliverables
                if d in CHANNEL_DELIVERABLES.get(channel, [])
            ]
            if not channel_deliverables:
                channel_deliverables = CHANNEL_DELIVERABLES.get(channel, [Deliverable.POST])

            for deliverable in channel_deliverables:
                render_tasks.append((channel, deliverable))

        # Execute all renders in parallel (I/O-bound LLM calls)
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def render_one(args):
            ch, deliv = args
            # Each thread gets its own trace to avoid race conditions
            thread_trace = NodeTrace(
                node_name=f"channel_renderer_{ch.value}_{deliv.value}",
                started_at=datetime.now(),
            )
            piece = _render_single_piece(
                channel=ch, deliverable=deliv,
                brief=brief, master_message=master_message,
                context_pack=context_pack, config=config, node_trace=thread_trace,
            )
            return piece, thread_trace

        total_tokens = {"input": 0, "output": 0}
        errors = []

        with ThreadPoolExecutor(max_workers=len(render_tasks)) as executor:
            futures = {executor.submit(render_one, task): task for task in render_tasks}
            for future in as_completed(futures):
                piece, thread_trace = future.result()
                if piece:
                    all_pieces.append(piece)
                # Aggregate token usage from each thread safely
                if thread_trace.token_usage:
                    total_tokens["input"] += thread_trace.token_usage.get("input", 0)
                    total_tokens["output"] += thread_trace.token_usage.get("output", 0)
                if thread_trace.error:
                    errors.append(thread_trace.error)
                if thread_trace.model_used:
                    node_trace.model_used = thread_trace.model_used

        # Sort pieces by channel order (facebook → instagram → tiktok)
        channel_order = {Channel.FACEBOOK: 0, Channel.INSTAGRAM: 1, Channel.TIKTOK: 2}
        all_pieces.sort(key=lambda p: (channel_order.get(p.channel, 99), p.deliverable.value))

        node_trace.token_usage = total_tokens
        if errors:
            node_trace.error = "\n".join(errors)

        campaign_content = CampaignContent(
            pieces=all_pieces,
            master_message_summary=master_message.core_promise,
        )

        node_trace.output_summary = f"Generated {len(all_pieces)} content pieces"
        node_trace.finished_at = datetime.now()

        return {
            "campaign_content": campaign_content,
            "current_node": "channel_renderer",
            "trace": update_trace(state, node_trace),
        }

    except Exception as e:
        node_trace.error = f"Channel rendering failed: {str(e)}"
        node_trace.finished_at = datetime.now()
        return {
            "error": node_trace.error,
            "current_node": "channel_renderer",
            "trace": update_trace(state, node_trace),
        }


def _render_single_piece(
    channel: Channel,
    deliverable: Deliverable,
    brief,
    master_message,
    context_pack: dict,
    config: dict,
    node_trace: NodeTrace,
) -> ContentPiece | None:
    """Render a single content piece for a specific channel + deliverable."""
    try:
        llm = ChatAnthropic(
            model=config["model"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            api_key=get_api_key(),
        )

        system_prompt = _load_channel_prompt(channel.value)

        # Build user message with all context
        voice_profile = context_pack.get("voice_profile", {})
        platform_rules = context_pack.get("platform_rules", {}).get(channel.value, "")

        user_parts = [
            f"## Master Message\n```json\n{master_message.model_dump_json(indent=2)}\n```",
            f"## Voice Profile\n```json\n{json.dumps(voice_profile, ensure_ascii=False, indent=2)}\n```",
            f"## Platform Rules\n{platform_rules}",
            f"## Campaign Brief\n```json\n{brief.model_dump_json(indent=2)}\n```",
            f"## Deliverable Type: {deliverable.value}",
            f"## Content Policies\n{context_pack.get('policies', '')}",
        ]

        user_message = "\n\n---\n\n".join(user_parts)

        # Use structured output for ContentPiece
        structured_llm = llm.with_structured_output(ContentPiece)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Tạo {deliverable.value} cho {channel.value}:\n\n{user_message}"),
        ]

        handler = TokenUsageHandler()
        piece = structured_llm.invoke(messages, config={"callbacks": [handler]})

        # Ensure channel and deliverable are set correctly
        piece.channel = channel
        piece.deliverable = deliverable

        # Calculate word count
        piece.word_count = len(piece.body.split())

        # Post-processing: deduplicate headline/hook/body
        piece = _dedup_content_fields(piece)

        # Post-processing: ensure hashtag prefix + force lowercase + limit count
        piece.hashtags = [
            (h if h.startswith("#") else f"#{h}").lower()
            for h in piece.hashtags
        ]
        # Limit hashtags per platform
        max_hashtags = 5 if channel == Channel.FACEBOOK else 10
        piece.hashtags = piece.hashtags[:max_hashtags]

        # Token usage tracking
        node_trace.model_used = config["model"]
        if handler.has_data:
            node_trace.token_usage = handler.get_usage()
        else:
            node_trace.token_usage = {
                "input": estimate_tokens(system_prompt + user_message),
                "output": estimate_tokens(piece.model_dump_json()),
            }

        return piece

    except Exception as e:
        # Log error but don't fail entire pipeline for one piece
        node_trace.error = (node_trace.error or "") + f"\nFailed {channel.value}/{deliverable.value}: {str(e)}"
        return None


def _dedup_content_fields(piece: ContentPiece) -> ContentPiece:
    """
    Remove duplicate content between headline, hook, and body first line.

    Common LLM behavior: putting the same text in headline, hook,
    and the first line of body. This function deduplicates.
    """
    body_first_line = piece.body.split("\n")[0].strip() if piece.body else ""

    # If headline is the same as hook or body first line, clear it
    if piece.headline and piece.hook:
        if _text_similar(piece.headline, piece.hook):
            piece.headline = None

    if piece.headline and body_first_line:
        if _text_similar(piece.headline, body_first_line):
            piece.headline = None

    # If hook is the same as body first line, clear hook
    # (body already contains it)
    if piece.hook and body_first_line:
        if _text_similar(piece.hook, body_first_line):
            piece.hook = None

    return piece


def _text_similar(a: str, b: str) -> bool:
    """Check if two text strings are essentially the same (ignoring minor differences)."""
    def normalize(s):
        return s.strip().rstrip("?!.…").strip()
    return normalize(a) == normalize(b)
