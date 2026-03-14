#!/usr/bin/env python3
"""
Publish meeting transcript to Notion.

Configuration:
- PARENT_PAGE_ID: The Notion page ID where meeting transcriptions will be created as subpages.
  Share this page with your Notion integration.
"""

import json
import sys
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

NOTION_VERSION = "2025-09-03"

# Configuration - set your parent page ID here
# This is where all meeting transcription pages will be created
PARENT_PAGE_ID = "YOUR_PARENT_PAGE_ID_HERE"  # e.g., "3002493c-7493-8103-b466-cc1b3da35917"

console = Console()


def get_notion_key():
    key_path = Path.home() / ".config" / "notion" / "api_key"
    if key_path.exists():
        return key_path.read_text().strip()
    raise RuntimeError("Notion API key not found at ~/.config/notion/api_key")


def headers():
    return {
        "Authorization": f"Bearer {get_notion_key()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def rich_text(content: str, bold: bool = False) -> dict:
    return {
        "type": "text",
        "text": {"content": content[:2000]},  # Notion limit
        "annotations": {"bold": bold},
    }


def chunk_text(text: str, max_len: int = 2000) -> list:
    """Split text into chunks at line boundaries."""
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line[:max_len]
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks


def create_meeting_page(
    title: str,
    date: str,
    analysis: dict,
    transcript_data: dict,
    parent_page_id: str = None,
    verbose: bool = False,
) -> str:
    """Create a Notion page with meeting notes."""
    
    parent_id = parent_page_id or PARENT_PAGE_ID
    
    if parent_id == "YOUR_PARENT_PAGE_ID_HERE":
        console.print("[red]Error: Please set PARENT_PAGE_ID in the script or pass --parent-page[/red]")
        sys.exit(1)
    
    speakers = transcript_data.get("speakers", [])
    duration = transcript_data.get("duration_minutes", 0)
    talk_ratios = transcript_data.get("talk_ratios", [])
    transcript_lines = transcript_data.get("transcript", [])
    cost = transcript_data.get("cost_usd", 0)
    processing_time = transcript_data.get("processing_time_seconds", 0)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("[cyan]Creating Notion page...", total=None)
        
        # Build page content
        children = []
        
        # Metadata callout
        meta_text = f"📅 {date} | ⏱️ {duration} min | 👥 {', '.join(speakers)}\n"
        meta_text += " | ".join(talk_ratios)
        if cost:
            meta_text += f"\n💰 Transcription cost: ${cost:.2f} | Processing: {processing_time:.0f}s"
        
        children.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [rich_text(meta_text)],
                "icon": {"type": "emoji", "emoji": "📊"},
            },
        })
        
        # Summary
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [rich_text("📋 Summary")]},
        })
        summary = analysis.get("summary", "No summary generated.")
        for chunk in chunk_text(summary):
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [rich_text(chunk)]},
            })
        
        # Desired Outcome
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [rich_text("🎯 Desired Outcome")]},
        })
        outcome = analysis.get("desired_outcome", "Not assessed.")
        for chunk in chunk_text(outcome):
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [rich_text(chunk)]},
            })
        
        # Action Items
        action_items = analysis.get("action_items", [])
        if action_items:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [rich_text("✅ Action Items")]},
            })
            for item in action_items:
                owner = item.get("owner", "TBD")
                action = item.get("action", "")
                due = item.get("due", "")
                text = f"{action}"
                if owner:
                    text += f" — {owner}"
                if due:
                    text += f" (by {due})"
                children.append({
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [rich_text(text)],
                        "checked": False,
                    },
                })
        
        # Key Decisions
        decisions = analysis.get("decisions", [])
        if decisions:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [rich_text("🔑 Key Decisions")]},
            })
            for decision in decisions:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [rich_text(decision)]},
                })
        
        # Discussion Topics
        topics = analysis.get("discussion_topics", [])
        if topics:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [rich_text("💬 Discussion Topics")]},
            })
            for topic in topics:
                topic_title = topic.get("title", "")
                topic_summary = topic.get("summary", "")
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [rich_text(topic_title)]},
                })
                if topic_summary:
                    for chunk in chunk_text(topic_summary):
                        children.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {"rich_text": [rich_text(chunk)]},
                        })
        
        # Parking Lot
        parking = analysis.get("parking_lot", [])
        if parking:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [rich_text("🅿️ Parking Lot")]},
            })
            for item in parking:
                children.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [rich_text(item)]},
                })
        
        # Professional Coaching
        coaching = analysis.get("professional_coaching")
        if coaching:
            children.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [rich_text("🎯 Professional Coaching")]},
            })
            
            # Overall assessment
            if coaching.get("overall_assessment"):
                for chunk in chunk_text(coaching["overall_assessment"]):
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [rich_text(chunk)]},
                    })
            
            # Strengths
            strengths = coaching.get("strengths", [])
            if strengths:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [rich_text("✅ Strengths")]},
                })
                for s in strengths:
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [rich_text(s)]},
                    })
            
            # Growth areas
            growth = coaching.get("growth_areas", [])
            if growth:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [rich_text("📈 Growth Areas")]},
                })
                for g in growth:
                    children.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [rich_text(g)]},
                    })
            
            # Competencies (in a toggle for cleanliness)
            competencies = coaching.get("competencies", {})
            if competencies:
                comp_blocks = []
                rating_emoji = {"strong": "🟢", "developing": "🟡", "not_observed": "⚪"}
                
                for comp_key, comp_data in competencies.items():
                    if isinstance(comp_data, dict) and comp_data.get("observed"):
                        rating = comp_data.get("rating", "not_observed")
                        emoji = rating_emoji.get(rating, "⚪")
                        name = comp_key.replace("_", " ").title()
                        notes = comp_data.get("notes", "")
                        text = f"{emoji} {name}: {notes}" if notes else f"{emoji} {name}"
                        comp_blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": [rich_text(text[:2000])]},
                        })
                
                if comp_blocks:
                    children.append({
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [rich_text("📊 Competency Details")],
                            "children": comp_blocks,
                        },
                    })
            
            # Recommendations
            recs = coaching.get("recommendations", [])
            if recs:
                children.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [rich_text("💡 Recommendations")]},
                })
                for r in recs:
                    children.append({
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {"rich_text": [rich_text(r)]},
                    })
        
        # Full Transcript
        children.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [rich_text("📝 Full Transcript")]},
        })
        
        # Build transcript blocks - split into multiple toggles if needed
        # Notion limit: 100 children per toggle block
        TOGGLE_BATCH_SIZE = 95  # Leave some margin
        
        def build_transcript_block(line: str) -> dict:
            """Convert a transcript line to a Notion block."""
            if line.startswith("**") and "**" in line[2:]:
                end_bold = line.index("**", 2)
                speaker = line[2:end_bold]
                rest = line[end_bold + 2:]
                return {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            rich_text(speaker, bold=True),
                            rich_text(rest[:1900])
                        ]
                    },
                }
            else:
                return {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [rich_text(line[:2000])]},
                }
        
        # Get timestamps for labeling toggles
        def get_timestamp_for_line(idx: int) -> str:
            """Extract timestamp from transcript line or estimate from position."""
            if idx < len(transcript_lines):
                line = transcript_lines[idx]
                # Format: **Speaker** [MM:SS]: text
                if "[" in line and "]" in line:
                    start = line.index("[") + 1
                    end = line.index("]")
                    return line[start:end]
            return "..."
        
        total_lines = len(transcript_lines)
        
        if total_lines <= TOGGLE_BATCH_SIZE:
            # Single toggle for short transcripts
            transcript_blocks = [build_transcript_block(line) for line in transcript_lines]
            children.append({
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [rich_text(f"Click to expand ({total_lines} exchanges)")],
                    "children": transcript_blocks,
                },
            })
        else:
            # Multiple toggles for long transcripts
            for batch_start in range(0, total_lines, TOGGLE_BATCH_SIZE):
                batch_end = min(batch_start + TOGGLE_BATCH_SIZE, total_lines)
                batch_lines = transcript_lines[batch_start:batch_end]
                
                # Get time range for this batch
                start_time = get_timestamp_for_line(batch_start)
                end_time = get_timestamp_for_line(batch_end - 1)
                
                transcript_blocks = [build_transcript_block(line) for line in batch_lines]
                
                part_num = (batch_start // TOGGLE_BATCH_SIZE) + 1
                total_parts = (total_lines + TOGGLE_BATCH_SIZE - 1) // TOGGLE_BATCH_SIZE
                
                toggle_label = f"Part {part_num}/{total_parts}: [{start_time}] – [{end_time}] ({len(batch_lines)} exchanges)"
                
                children.append({
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [rich_text(toggle_label)],
                        "children": transcript_blocks,
                    },
                })
        
        progress.update(task, description="[cyan]Uploading to Notion...")
        
        if verbose:
            console.print(f"[dim]Creating page under parent: {parent_id}[/dim]")
            console.print(f"[dim]Total blocks: {len(children)}[/dim]")
        
        # Create the page
        payload = {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "🎙️"},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            },
            "children": children[:100],
        }
        
        resp = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers(),
            json=payload,
        )
        
        if resp.status_code != 200:
            console.print(f"[red]Notion error ({resp.status_code}): {resp.text}[/red]")
            sys.exit(1)
        
        page = resp.json()
        page_id = page["id"]
        
        # Append remaining blocks
        remaining = children[100:]
        batch_num = 1
        while remaining:
            batch = remaining[:100]
            remaining = remaining[100:]
            
            if verbose:
                console.print(f"[dim]Appending batch {batch_num} ({len(batch)} blocks)...[/dim]")
            
            resp = requests.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers(),
                json={"children": batch},
            )
            if resp.status_code != 200:
                console.print(f"[yellow]Warning: Failed to append batch {batch_num}[/yellow]")
            batch_num += 1
        
        progress.update(task, description="[green]✓ Page created")
    
    page_url = page.get("url", f"https://notion.so/{page_id.replace('-', '')}")
    
    # Summary
    console.print()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="green", justify="right")
    summary.add_column(style="white")
    summary.add_row("📄 Page:", title)
    summary.add_row("🔗 URL:", page_url)
    
    console.print(Panel(summary, title="[bold green]Notion Page Created[/bold green]", border_style="green"))
    
    return page_url


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Publish meeting transcript to Notion")
    parser.add_argument("title", help="Page title")
    parser.add_argument("date", help="Meeting date (YYYY-MM-DD)")
    parser.add_argument("analysis", help="Analysis JSON file")
    parser.add_argument("transcript", nargs="?", help="Transcript JSON file")
    parser.add_argument("--parent-page", "-p", help="Parent page ID (overrides PARENT_PAGE_ID)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    analysis = json.loads(Path(args.analysis).read_text())
    transcript_data = {}
    if args.transcript:
        transcript_data = json.loads(Path(args.transcript).read_text())
    
    url = create_meeting_page(
        args.title, 
        args.date, 
        analysis, 
        transcript_data, 
        parent_page_id=args.parent_page,
        verbose=args.verbose
    )
    print(url)
