#!/usr/bin/env python3
"""
View transcription cost history.
"""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

COST_LOG = Path.home() / ".config" / "meeting-transcriber" / "cost_log.json"

console = Console()


def show_costs():
    if not COST_LOG.exists():
        console.print("[yellow]No transcription history yet.[/yellow]")
        return
    
    log = json.loads(COST_LOG.read_text())
    
    # Summary
    total_cost = log.get("total_cost_usd", 0)
    total_duration = log.get("total_duration_seconds", 0)
    total_minutes = total_duration / 60
    entries = log.get("entries", [])
    
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="cyan", justify="right")
    summary.add_column(style="white")
    
    summary.add_row("Total Transcriptions:", str(len(entries)))
    summary.add_row("Total Audio:", f"{total_minutes:.1f} minutes")
    summary.add_row("Total Cost:", f"${total_cost:.2f}")
    summary.add_row("Avg Cost/Meeting:", f"${total_cost/len(entries):.2f}" if entries else "$0.00")
    
    console.print(Panel(summary, title="[bold blue]Transcription Costs[/bold blue]", border_style="blue"))
    
    # Recent entries
    if entries:
        console.print()
        table = Table(title="Recent Transcriptions")
        table.add_column("Date", style="dim")
        table.add_column("File")
        table.add_column("Duration", justify="right")
        table.add_column("Cost", justify="right", style="green")
        
        for entry in entries[-10:]:  # Last 10
            date = entry.get("date", "")[:10]
            file = entry.get("file", "")[:40]
            dur = entry.get("duration_seconds", 0) / 60
            cost = entry.get("cost_usd", 0)
            table.add_row(date, file, f"{dur:.1f}m", f"${cost:.2f}")
        
        console.print(table)


if __name__ == "__main__":
    show_costs()
