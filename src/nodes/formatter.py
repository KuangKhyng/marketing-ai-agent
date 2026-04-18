"""
Formatter Node
- Input: CampaignContent (reviewed & passed) + RunTrace
- Output: final formatted output
- Model: None
- Type: Deterministic

Compiles final output in multiple formats:
- Console: Rich formatted output
- JSON: structured output
- Markdown: human-readable file saved to outputs/
"""
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown as RichMarkdown

from src.models.trace import NodeTrace, RunTrace
from src.config.settings import PROJECT_ROOT

OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def formatter_node(state: dict) -> dict:
    """
    Format and save the final campaign output.

    Args:
        state: CampaignState dict with 'campaign_content', 'review_result',
               'brief', 'trace'.

    Returns:
        Updated state with finalized trace.
    """
    node_trace = NodeTrace(
        node_name="formatter",
        started_at=datetime.now(),
        input_summary=f"Formatting {len(state['campaign_content'].pieces)} content pieces",
    )

    try:
        trace = state.get("trace") or RunTrace()
        run_id = trace.run_id
        content = state["campaign_content"]
        brief = state["brief"]
        review_result = state.get("review_result")

        # Create output directory
        run_dir = OUTPUTS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save as Markdown
        markdown_content = _build_markdown(content, brief, review_result, trace)
        md_path = run_dir / "content.md"
        md_path.write_text(markdown_content, encoding="utf-8")

        # 2. Save as JSON
        json_output = _build_json(content, brief, review_result, trace)
        json_path = run_dir / "content.json"
        json_path.write_text(
            json.dumps(json_output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 3. Save trace
        trace_path = run_dir / "trace.json"
        trace_path.write_text(
            trace.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # 4. Print to console
        _print_console_output(content, brief, review_result, trace, run_dir)

        node_trace.output_summary = f"Saved to {run_dir}"
        node_trace.finished_at = datetime.now()

        # Finalize trace
        trace.node_traces.append(node_trace)
        trace.finished_at = datetime.now()
        trace.final_status = "completed"
        trace.brief_summary = f"Campaign for {brief.offer.product_or_service}: {brief.goal.value}"

        # Re-save trace with final status
        trace_path.write_text(
            trace.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return {
            "current_node": "formatter",
            "trace": trace,
        }

    except Exception as e:
        node_trace.error = f"Formatting failed: {str(e)}"
        node_trace.finished_at = datetime.now()
        trace = state.get("trace") or RunTrace()
        trace.node_traces.append(node_trace)
        trace.final_status = "failed"
        return {
            "error": node_trace.error,
            "current_node": "formatter",
            "trace": trace,
        }


def _build_markdown(content, brief, review_result, trace) -> str:
    """Build markdown output file."""
    lines = [
        f"# Campaign Content — {brief.offer.product_or_service}",
        f"",
        f"**Run ID:** {trace.run_id}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Goal:** {brief.goal.value}",
        f"**Channels:** {', '.join(c.value for c in brief.channels)}",
        f"",
        f"---",
        f"",
        f"## Master Message",
        f"",
        f"> {content.master_message_summary}",
        f"",
        f"---",
    ]

    # Group content by channel
    pieces_by_channel = {}
    for piece in content.pieces:
        key = piece.channel.value
        if key not in pieces_by_channel:
            pieces_by_channel[key] = []
        pieces_by_channel[key].append(piece)

    for channel, pieces in pieces_by_channel.items():
        lines.append(f"")
        lines.append(f"## {channel.upper()}")
        lines.append(f"")

        for piece in pieces:
            lines.append(f"### {piece.deliverable.value.replace('_', ' ').title()}")
            lines.append(f"")
            if piece.headline:
                lines.append(f"**Headline:** {piece.headline}")
                lines.append(f"")
            if piece.hook:
                lines.append(f"**Hook:** {piece.hook}")
                lines.append(f"")
            lines.append(piece.body)
            lines.append(f"")
            if piece.cta_text:
                lines.append(f"**CTA:** {piece.cta_text}")
                lines.append(f"")
            if piece.hashtags:
                lines.append(f"**Hashtags:** {' '.join(piece.hashtags)}")
                lines.append(f"")
            if piece.visual_direction:
                lines.append(f"**Visual Direction:** {piece.visual_direction}")
                lines.append(f"")
            if piece.notes:
                lines.append(f"**Notes:** {piece.notes}")
                lines.append(f"")
            lines.append(f"*Word count: {piece.word_count}*")
            lines.append(f"")
            lines.append(f"---")

    # Review scores
    if review_result:
        lines.append(f"")
        lines.append(f"## Review Scores")
        lines.append(f"")
        lines.append(f"| Dimension | Score | Passed |")
        lines.append(f"|-----------|-------|--------|")
        for score in review_result.dimension_scores:
            status = "✅" if score.passed else "❌"
            lines.append(f"| {score.dimension.value} | {score.score:.2f} | {status} |")
        lines.append(f"")
        lines.append(f"**Overall:** {'✅ PASSED' if review_result.overall_passed else '❌ FAILED'}")

    return "\n".join(lines)


def _build_json(content, brief, review_result, trace) -> dict:
    """Build structured JSON output."""
    return {
        "run_id": trace.run_id,
        "timestamp": datetime.now().isoformat(),
        "brief": json.loads(brief.model_dump_json()),
        "content": json.loads(content.model_dump_json()),
        "review": json.loads(review_result.model_dump_json()) if review_result else None,
        "trace_summary": {
            "total_nodes": len(trace.node_traces),
            "revision_count": trace.revision_count,
            "cost_estimate": trace.total_cost_estimate,
        },
    }


def _print_console_output(content, brief, review_result, trace, run_dir):
    """Print formatted output to console using Rich."""
    console = Console()

    console.print()
    console.print(Panel(
        f"[bold cyan]Campaign Content — {brief.offer.product_or_service}[/bold cyan]\n"
        f"Run ID: {trace.run_id} | Goal: {brief.goal.value} | "
        f"Channels: {', '.join(c.value for c in brief.channels)}",
        title="✨ Marketing Agent Output",
        border_style="cyan",
    ))

    # Content pieces
    for piece in content.pieces:
        channel_color = {
            "facebook": "blue",
            "instagram": "magenta",
            "tiktok": "red",
        }.get(piece.channel.value, "white")

        header = f"[bold {channel_color}]{piece.channel.value.upper()}[/bold {channel_color}] — {piece.deliverable.value}"

        panel_content = ""
        if piece.hook:
            panel_content += f"[bold yellow]Hook:[/bold yellow] {piece.hook}\n\n"
        panel_content += piece.body
        if piece.cta_text:
            panel_content += f"\n\n[bold green]CTA:[/bold green] {piece.cta_text}"
        if piece.hashtags:
            panel_content += f"\n\n[dim]{' '.join(piece.hashtags)}[/dim]"

        console.print(Panel(
            panel_content,
            title=header,
            border_style=channel_color,
            padding=(1, 2),
        ))

    # Review scores table
    if review_result:
        table = Table(title="Review Scores", border_style="cyan")
        table.add_column("Dimension", style="bold")
        table.add_column("Score", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Feedback")

        for score in review_result.dimension_scores:
            status = "[green]✅ PASS[/green]" if score.passed else "[red]❌ FAIL[/red]"
            score_color = "green" if score.passed else "red"
            table.add_row(
                score.dimension.value,
                f"[{score_color}]{score.score:.2f}[/{score_color}]",
                status,
                score.feedback[:60] + "..." if len(score.feedback) > 60 else score.feedback,
            )

        console.print(table)

        overall = "[bold green]✅ PASSED[/bold green]" if review_result.overall_passed else "[bold red]❌ FAILED[/bold red]"
        console.print(f"\nOverall: {overall}")

    console.print(f"\n[dim]Output saved to: {run_dir}[/dim]")
    console.print(f"[dim]Estimated cost: ${trace.total_cost_estimate:.4f}[/dim]")
    console.print()
