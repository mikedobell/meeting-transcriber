#!/usr/bin/env python3
"""
Email meeting transcript summary via gog CLI.

Configuration:
- FROM_EMAIL: Email address to send from (must be authenticated in gog)
- DEFAULT_TO: Default recipient email address

These should be customized for your setup.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

from rich.console import Console

console = Console()

# Configuration - customize these for your setup
FROM_EMAIL = "your-email@example.com"  # Must be authenticated in gog
DEFAULT_TO = "recipient@example.com"   # Default recipient


def build_email_body(
    title: str,
    date: str,
    analysis: dict,
    transcript_data: dict,
    notion_url: str = None,
) -> str:
    """Build email body with summary and transcript excerpt."""
    
    speakers = transcript_data.get("speakers", [])
    duration = transcript_data.get("duration_minutes", 0)
    talk_ratios = transcript_data.get("talk_ratios", [])
    transcript_lines = transcript_data.get("transcript", [])
    cost = transcript_data.get("cost_usd", 0)
    
    lines = []
    
    # Header
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"**Date:** {date}")
    lines.append(f"**Duration:** {duration} minutes")
    lines.append(f"**Speakers:** {', '.join(speakers)}")
    lines.append(f"**Talk ratios:** {' | '.join(talk_ratios)}")
    if cost:
        lines.append(f"**Transcription cost:** ${cost:.2f}")
    lines.append("")
    
    # Notion link
    if notion_url:
        lines.append(f"📄 **Full notes:** {notion_url}")
        lines.append("")
    
    # Summary
    lines.append("---")
    lines.append("")
    lines.append("## 📋 Summary")
    lines.append("")
    lines.append(analysis.get("summary", "No summary available."))
    lines.append("")
    
    # Desired Outcome
    if analysis.get("desired_outcome"):
        lines.append("## 🎯 Desired Outcome")
        lines.append("")
        lines.append(analysis.get("desired_outcome"))
        lines.append("")
    
    # Action Items
    action_items = analysis.get("action_items", [])
    if action_items:
        lines.append("## ✅ Action Items")
        lines.append("")
        for item in action_items:
            owner = item.get("owner", "TBD")
            action = item.get("action", "")
            due = item.get("due", "")
            line = f"- [ ] {action}"
            if owner:
                line += f" — {owner}"
            if due:
                line += f" (by {due})"
            lines.append(line)
        lines.append("")
    
    # Key Decisions
    decisions = analysis.get("decisions", [])
    if decisions:
        lines.append("## 🔑 Key Decisions")
        lines.append("")
        for decision in decisions:
            lines.append(f"- {decision}")
        lines.append("")
    
    # Professional Coaching
    coaching = analysis.get("professional_coaching")
    if coaching:
        lines.append("## 🎯 Professional Coaching")
        lines.append("")
        
        if coaching.get("overall_assessment"):
            lines.append(coaching["overall_assessment"])
            lines.append("")
        
        strengths = coaching.get("strengths", [])
        if strengths:
            lines.append("**Strengths:**")
            for s in strengths:
                lines.append(f"- ✅ {s}")
            lines.append("")
        
        growth = coaching.get("growth_areas", [])
        if growth:
            lines.append("**Growth Areas:**")
            for g in growth:
                lines.append(f"- 📈 {g}")
            lines.append("")
        
        # Competencies summary (just observed ones with strong/developing)
        competencies = coaching.get("competencies", {})
        rating_emoji = {"strong": "🟢", "developing": "🟡"}
        comp_lines = []
        for comp_key, comp_data in competencies.items():
            if isinstance(comp_data, dict) and comp_data.get("observed"):
                rating = comp_data.get("rating", "")
                if rating in rating_emoji:
                    name = comp_key.replace("_", " ").title()
                    comp_lines.append(f"- {rating_emoji[rating]} {name}")
        if comp_lines:
            lines.append("**Competencies Observed:**")
            lines.extend(comp_lines)
            lines.append("")
        
        recs = coaching.get("recommendations", [])
        if recs:
            lines.append("**Recommendations:**")
            for i, r in enumerate(recs, 1):
                lines.append(f"{i}. {r}")
            lines.append("")
    
    # Transcript excerpt (first 15 exchanges)
    lines.append("---")
    lines.append("")
    lines.append("## 📝 Transcript Excerpt")
    lines.append("")
    lines.append("*(First 15 exchanges — see Notion for full transcript)*")
    lines.append("")
    
    for line in transcript_lines[:15]:
        # Convert markdown bold to plain text for email
        line = line.replace("**", "")
        lines.append(f"> {line}")
        lines.append(">")
    
    if len(transcript_lines) > 15:
        lines.append(f"*... and {len(transcript_lines) - 15} more exchanges*")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Transcribed via AssemblyAI*")
    
    return "\n".join(lines)


def send_email(
    subject: str,
    body: str,
    to: str = None,
    from_account: str = None,
    verbose: bool = False,
) -> bool:
    """Send email via gog CLI."""
    
    to = to or DEFAULT_TO
    from_account = from_account or FROM_EMAIL
    
    if verbose:
        console.print(f"[dim]Sending email to {to} from {from_account}[/dim]")
        console.print(f"[dim]Subject: {subject}[/dim]")
    
    # Use gog gmail send command
    cmd = [
        "gog", "gmail", "send",
        "--account", from_account,
        "--to", to,
        "--subject", subject,
        "--body", body,
        "--no-input",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ Email sent to {to}[/green]")
            return True
        else:
            console.print(f"[red]Email failed: {result.stderr}[/red]")
            if verbose:
                console.print(f"[dim]stdout: {result.stdout}[/dim]")
            return False
    
    except subprocess.TimeoutExpired:
        console.print("[red]Email send timed out[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]gog CLI not found. Install with: npm install -g gog[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Email error: {e}[/red]")
        return False


def send_meeting_summary(
    title: str,
    date: str,
    analysis: dict,
    transcript_data: dict,
    notion_url: str = None,
    to: str = None,
    verbose: bool = False,
) -> bool:
    """Send meeting summary email."""
    
    subject = f"📝 {title}"
    body = build_email_body(title, date, analysis, transcript_data, notion_url)
    
    return send_email(subject, body, to=to, verbose=verbose)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Email meeting transcript summary")
    parser.add_argument("title", help="Meeting title")
    parser.add_argument("date", help="Meeting date")
    parser.add_argument("analysis", help="Analysis JSON file")
    parser.add_argument("transcript", help="Transcript JSON file")
    parser.add_argument("--notion-url", "-u", help="Notion page URL")
    parser.add_argument("--to", default=DEFAULT_TO, help="Recipient email")
    parser.add_argument("--from", dest="from_email", default=FROM_EMAIL, help="Sender email")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    analysis = json.loads(Path(args.analysis).read_text())
    transcript_data = json.loads(Path(args.transcript).read_text())
    
    success = send_meeting_summary(
        title=args.title,
        date=args.date,
        analysis=analysis,
        transcript_data=transcript_data,
        notion_url=args.notion_url,
        to=args.to,
        verbose=args.verbose,
    )
    
    sys.exit(0 if success else 1)
