"""
CLI Interface — main entry point for the Marketing Agent Workflow Engine.

Commands:
  python cli.py run "Tạo campaign cho dịch vụ tử vi online target Gen Z"
  python cli.py run --interactive
  python cli.py eval
  python cli.py analyze-voice
"""
import sys
import os
import argparse
import uuid
from datetime import datetime

# Fix Windows console encoding for Vietnamese text
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown as RichMarkdown

from src.graph.workflow import build_workflow
from src.models.trace import RunTrace
from langgraph.types import Command


console = Console()


def run_campaign(input_text: str = None, interactive: bool = False):
    """Run the full campaign generation pipeline."""
    console.print()
    console.print(Panel(
        "[bold cyan]Marketing Agent Workflow Engine[/bold cyan]\n"
        "[dim]Powered by LangGraph + Claude API[/dim]",
        border_style="cyan",
    ))

    # Get input
    if interactive or not input_text:
        console.print("\n[bold]Nhập yêu cầu campaign của bạn:[/bold]")
        console.print("[dim](Ví dụ: Tạo campaign awareness cho dịch vụ tử vi online, target Gen Z quan tâm tâm linh)[/dim]\n")
        input_text = Prompt.ask("[bold cyan]Campaign request[/bold cyan]")

    if not input_text.strip():
        console.print("[red]Error: Vui lòng nhập yêu cầu campaign.[/red]")
        return

    console.print(f"\n[dim]Processing: {input_text[:80]}...[/dim]\n")

    # Build workflow
    workflow = build_workflow()

    # Initial state
    initial_state = {
        "raw_input": input_text,
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

    # Thread config for checkpointer
    thread_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Run the workflow — it will interrupt at human_approval
        console.print("[bold yellow]⏳ Step 1/6: Parsing brief...[/bold yellow]")
        console.print("[bold yellow]⏳ Step 2/6: Building context...[/bold yellow]")
        console.print("[bold yellow]⏳ Step 3/6: Generating strategy...[/bold yellow]")

        # Stream through the graph until interrupt
        for event in workflow.stream(initial_state, config=config, stream_mode="values"):
            current = event.get("current_node", "")
            if current == "brief_parser":
                brief = event.get("brief")
                if brief:
                    console.print(f"[green]✓ Brief parsed:[/green] goal={brief.goal.value}, channels={[c.value for c in brief.channels]}")
            elif current == "context_builder":
                if event.get("context_pack"):
                    console.print("[green]✓ Context assembled[/green]")
            elif current == "strategist":
                if event.get("strategy"):
                    console.print("[green]✓ Strategy generated[/green]")

            # Check for errors
            if event.get("error"):
                console.print(f"\n[red]❌ Error: {event['error']}[/red]")
                return

        # After interrupt — we need to handle human approval
        # Get the current state to display strategy
        current_state = workflow.get_state(config)

        if current_state.next and "human_approval" in current_state.next:
            strategy = current_state.values.get("strategy", "")
            _handle_human_approval(workflow, config, strategy)

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Pipeline cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Pipeline error: {str(e)}[/red]")
        raise


def _handle_human_approval(workflow, config, strategy: str):
    """Handle the human approval interaction."""
    console.print()
    console.print(Panel(
        strategy,
        title="📋 Campaign Strategy — Review Required",
        border_style="yellow",
        padding=(1, 2),
    ))
    console.print()

    while True:
        choice = Prompt.ask(
            "[bold yellow][A]pprove / [R]eject[/bold yellow]",
            choices=["a", "r"],
            default="a",
        )

        if choice == "a":
            # Approve
            console.print("\n[green]✓ Strategy approved. Continuing...[/green]\n")
            console.print("[bold yellow]⏳ Step 4/6: Building message architecture...[/bold yellow]")
            console.print("[bold yellow]⏳ Step 5/6: Rendering channel content...[/bold yellow]")
            console.print("[bold yellow]⏳ Step 6/6: Reviewing content...[/bold yellow]")

            # Resume workflow with approval
            for event in workflow.stream(
                Command(resume={"approved": True}),
                config=config,
                stream_mode="values",
            ):
                current = event.get("current_node", "")
                if current == "message_architect":
                    mm = event.get("master_message")
                    if mm:
                        console.print(f"[green]✓ Master message created: {mm.core_promise[:60]}...[/green]")
                elif current == "channel_renderer":
                    content = event.get("campaign_content")
                    if content:
                        console.print(f"[green]✓ Content rendered: {len(content.pieces)} pieces[/green]")
                elif current == "reviewer":
                    review = event.get("review_result")
                    if review:
                        status = "[green]PASSED[/green]" if review.overall_passed else "[red]FAILED[/red]"
                        console.print(f"[green]✓ Review: {status}[/green]")
                        revision_count = event.get("revision_count", 0)
                        if not review.overall_passed and revision_count < event.get("max_revisions", 2):
                            console.print(f"[yellow]  ↻ Revision {revision_count}/{event.get('max_revisions', 2)} — retrying...[/yellow]")
                elif current == "formatter":
                    console.print("[green]✓ Output formatted and saved[/green]")

                if event.get("error"):
                    console.print(f"\n[red]❌ Error: {event['error']}[/red]")

            # Show post-workflow summary (Fix #10)
            _print_run_summary(workflow, config)

            break

        elif choice == "r":
            # Reject
            console.print("\n[red]✗ Strategy rejected. Ending workflow.[/red]")

            # Resume with rejection
            for event in workflow.stream(
                Command(resume={"approved": False}),
                config=config,
                stream_mode="values",
            ):
                pass

            break


def _print_run_summary(workflow, config):
    """Print post-workflow summary with revision info, cost, and any errors."""
    try:
        final_state = workflow.get_state(config)
        state_values = final_state.values

        revision_count = state_values.get("revision_count", 0)
        if revision_count > 0:
            console.print(f"\n[yellow]⚠️ Content was revised {revision_count} time(s) before passing review.[/yellow]")

        trace = state_values.get("trace")
        if trace:
            console.print(f"[dim]Total nodes executed: {len(trace.node_traces)}[/dim]")
            console.print(f"[dim]Estimated cost: ${trace.total_cost_estimate:.4f}[/dim]")
            errors = [nt for nt in trace.node_traces if nt.error]
            if errors:
                console.print(f"[yellow]⚠️ {len(errors)} node(s) had warnings/errors:[/yellow]")
                for nt in errors:
                    console.print(f"[yellow]  - {nt.node_name}: {nt.error[:80]}[/yellow]")
    except Exception:
        pass  # Don't let summary printing crash the CLI


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Marketing Agent Workflow Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py run "Tạo campaign cho dịch vụ tử vi online target Gen Z"
  python cli.py run --interactive
  python cli.py eval
  python cli.py analyze-voice
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run the campaign generation pipeline")
    run_parser.add_argument("input", nargs="?", help="Campaign request (natural language)")
    run_parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    # eval command (Phase 2)
    eval_parser = subparsers.add_parser("eval", help="Run evaluation on golden dataset")

    # analyze-voice command (Phase 2)
    voice_parser = subparsers.add_parser("analyze-voice", help="Analyze sample posts to create voice profile")

    args = parser.parse_args()

    if args.command == "run":
        run_campaign(input_text=args.input, interactive=args.interactive)
    elif args.command == "eval":
        console.print("[yellow]Evaluation runner is a Phase 2 feature.[/yellow]")
    elif args.command == "analyze-voice":
        console.print("[yellow]Voice analyzer is a Phase 2 feature.[/yellow]")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
