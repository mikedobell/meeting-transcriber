#!/usr/bin/env python3
"""
Full Meeting Transcription Pipeline
Transcribe → Analyze → Publish to Notion in one command.

Usage:
  python full_pipeline.py audio.m4a "Meeting with Sarah about Q3"
  python full_pipeline.py audio.m4a --title "Team Standup" --speakers 3
  
Note: Analysis is a placeholder — in production, integrate with your preferred LLM.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Import local modules
sys.path.insert(0, str(Path(__file__).parent))
from transcribe_aai import transcribe_meeting, save_backup, extract_names_from_context, apply_speaker_names
from notion_publish_simple import create_meeting_page
from email_summary import send_meeting_summary, DEFAULT_TO


def analyze_with_llm(transcript_data: dict, context: str = None) -> dict:
    """
    Placeholder for LLM analysis.
    
    In production, this should call your preferred LLM (Claude, GPT-4, etc.)
    to generate structured meeting notes.
    
    Expected output structure:
    {
        "summary": "Executive summary of the meeting",
        "desired_outcome": "What the meeting aimed to achieve and whether it did",
        "action_items": [
            {"owner": "Name", "action": "Task description", "due": "Date or timeframe"}
        ],
        "decisions": ["Key decisions made"],
        "discussion_topics": [
            {"title": "Topic name", "summary": "What was discussed"}
        ],
        "parking_lot": ["Items to revisit later"],
        "meeting_type": "Interview | Team Meeting | 1:1 | etc.",
        "professional_coaching": {
            "overall_assessment": "How did the user perform overall",
            "strengths": ["What they did well"],
            "growth_areas": ["What to improve"],
            "competencies": {
                "strategic_thinking": {
                    "observed": true/false,
                    "rating": "strong|developing|not_observed",
                    "notes": "Evidence and feedback"
                },
                ...
            },
            "recommendations": ["Specific actionable advice"]
        }
    }
    """
    
    # Placeholder - returns minimal valid structure
    speakers = transcript_data.get("speakers", [])
    duration = transcript_data.get("duration_minutes", 0)
    
    console.print("[yellow]⚠️  Analysis placeholder - integrate your LLM here[/yellow]")
    console.print("[dim]See analyze_with_llm() for expected output structure[/dim]")
    
    return {
        "summary": f"Meeting with {len(speakers)} participants, lasting {duration} minutes. "
                   f"Analysis not implemented - integrate your preferred LLM.",
        "desired_outcome": "Analysis not implemented",
        "action_items": [],
        "decisions": [],
        "discussion_topics": [],
        "parking_lot": [],
        "meeting_type": context or "Unknown",
    }


def run_pipeline(
    audio_path: str,
    title: str = None,
    speakers: int = None,
    context: str = None,
    names: list = None,
    verbose: bool = False,
    skip_notion: bool = False,
    send_email: bool = False,
    email_to: str = None,
) -> dict:
    """Run the full transcription pipeline."""
    
    audio_file = Path(audio_path)
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Default title from filename
    if not title:
        title = audio_file.stem.replace("-", " ").replace("_", " ").title()
    
    console.print(Panel(f"[bold blue]Meeting Transcriber Pipeline[/bold blue]\n{title}", border_style="blue"))
    
    # Step 1: Transcribe
    console.print("\n[bold cyan]Step 1:[/bold cyan] Transcribing audio...")
    transcript_data = transcribe_meeting(
        audio_path,
        speakers=speakers,
        context=context,
        names=names,
        verbose=verbose,
        notify=False,
    )
    
    # Save backup
    backup_path = save_backup(transcript_data, audio_path)
    if verbose:
        console.print(f"[dim]Backup: {backup_path}[/dim]")
    
    # Step 2: Analyze (placeholder)
    console.print("\n[bold cyan]Step 2:[/bold cyan] Analyzing transcript...")
    analysis = analyze_with_llm(transcript_data, context)
    
    # Step 3: Publish to Notion
    notion_url = None
    if not skip_notion:
        console.print("\n[bold cyan]Step 3:[/bold cyan] Publishing to Notion...")
        try:
            notion_url = create_meeting_page(
                title, date_str, analysis, transcript_data, verbose=verbose
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Notion publish failed: {e}[/yellow]")
    
    # Step 4: Email summary
    if send_email:
        console.print("\n[bold cyan]Step 4:[/bold cyan] Sending email summary...")
        send_meeting_summary(
            title=title,
            date=date_str,
            analysis=analysis,
            transcript_data=transcript_data,
            notion_url=notion_url,
            to=email_to or DEFAULT_TO,
            verbose=verbose,
        )
    
    # Final summary
    console.print()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="green", justify="right")
    summary.add_column(style="white")
    
    summary.add_row("✅ Status:", "Pipeline complete")
    summary.add_row("📁 Audio:", audio_file.name)
    summary.add_row("👥 Speakers:", ", ".join(transcript_data.get("speakers", [])))
    summary.add_row("⏱️  Duration:", f"{transcript_data.get('duration_minutes', 0)} min")
    summary.add_row("💰 Cost:", f"${transcript_data.get('cost_usd', 0):.2f}")
    if notion_url:
        summary.add_row("📄 Notion:", notion_url)
    
    console.print(Panel(summary, title="[bold green]Pipeline Complete[/bold green]", border_style="green"))
    
    return {
        "title": title,
        "date": date_str,
        "transcript": transcript_data,
        "analysis": analysis,
        "notion_url": notion_url,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Full Meeting Transcription Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s meeting.m4a "Interview with Sarah"
  %(prog)s meeting.m4a --title "Q4 Planning" --speakers 3
  %(prog)s meeting.m4a --skip-notion  # Transcribe only
  %(prog)s meeting.m4a --email --email-to you@example.com
        """
    )
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("context", nargs="?", default=None,
                        help="Meeting context (e.g., 'Interview with Sarah')")
    parser.add_argument("--title", "-t", default=None,
                        help="Meeting title (default: auto-generated from filename)")
    parser.add_argument("--speakers", "-s", type=int, help="Expected number of speakers")
    parser.add_argument("--names", "-n", help="Speaker names, comma-separated (e.g., 'Sarah,James')")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--skip-notion", action="store_true", help="Skip Notion publishing")
    parser.add_argument("--email", "-e", action="store_true", help="Send email summary")
    parser.add_argument("--email-to", default=None, help="Email recipient")
    parser.add_argument("--output", "-o", help="Save full result to JSON file")
    
    args = parser.parse_args()
    
    if not Path(args.audio).exists():
        console.print(f"[red]Error: File not found: {args.audio}[/red]")
        sys.exit(1)
    
    # Parse names
    names = None
    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
    
    result = run_pipeline(
        audio_path=args.audio,
        title=args.title,
        speakers=args.speakers,
        context=args.context,
        names=names,
        verbose=args.verbose,
        skip_notion=args.skip_notion,
        send_email=args.email,
        email_to=args.email_to,
    )
    
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, default=str))
        console.print(f"[blue]Full result saved to:[/blue] {args.output}")


if __name__ == "__main__":
    main()
