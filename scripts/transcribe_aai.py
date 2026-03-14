#!/usr/bin/env python3
"""
Meeting Transcriber — AssemblyAI Edition
Fast, reliable cloud-based transcription with speaker diarization.

Features:
- Rich TUI with progress display
- Verbose logging mode
- Auto-notification when complete
- Local backup of transcripts
- Cost tracking
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import assemblyai as aai
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table

# Configuration
TRANSCRIPTS_DIR = Path.home() / ".config" / "meeting-transcriber" / "transcripts"
COST_LOG = Path.home() / ".config" / "meeting-transcriber" / "cost_log.json"
COST_PER_SECOND = 0.00025  # $0.015/min = $0.00025/sec

console = Console()


def extract_names_from_context(context: str) -> list:
    """Extract participant names from context string."""
    if not context:
        return []
    
    names = []
    
    # Pattern to capture everything after "with"
    match = re.search(
        r"(?:meeting|call|interview|chat|discussion|sync|standup|1:1|one-on-one)\s+with\s+(.+)",
        context,
        re.IGNORECASE
    )
    
    if match:
        participants = match.group(1)
        # Split on "and", ",", "&"
        parts = re.split(r'\s+and\s+|\s*,\s*|\s*&\s*', participants)
        for part in parts:
            part = part.strip()
            # Remove common suffixes like "about X", "regarding Y", "from X"
            part = re.split(r'\s+(?:about|regarding|re:|for|on|from)\s+', part, flags=re.IGNORECASE)[0]
            part = part.strip()
            
            # Handle titles like Dr., Mr., Mrs., Ms.
            name_match = re.match(
                r'^((?:Dr|Mr|Mrs|Ms|Prof)\.?\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})',
                part
            )
            if name_match:
                title = name_match.group(1) or ""
                name = name_match.group(2)
                full_name = (title + name).strip()
                if full_name:
                    names.append(full_name)
    
    return names


def apply_speaker_names(transcript_data: dict, names: list, user_first: bool = True) -> dict:
    """Replace Speaker A/B labels with actual names."""
    if not names:
        return transcript_data
    
    # Build speaker mapping
    speaker_map = {}
    speakers = transcript_data.get("speakers", [])
    
    # Default: User is Speaker A (talks less in interviews, more in internal meetings)
    # Customize this logic for your use case
    user_name = "User"  # Replace with actual user name if desired
    
    if len(speakers) >= 1:
        if user_first:
            speaker_map["Speaker A"] = user_name
        if len(names) >= 1:
            if user_first:
                speaker_map["Speaker B"] = names[0]
            else:
                speaker_map["Speaker A"] = names[0]
                if len(speakers) >= 2:
                    speaker_map["Speaker B"] = user_name
        if len(names) >= 2 and len(speakers) >= 3:
            speaker_map["Speaker C"] = names[1]
    
    # Apply mapping to transcript
    def replace_speaker(text: str) -> str:
        for old, new in speaker_map.items():
            text = text.replace(f"**{old}**", f"**{new}**")
            text = text.replace(old, new)
        return text
    
    # Update transcript lines
    new_lines = [replace_speaker(line) for line in transcript_data.get("transcript", [])]
    transcript_data["transcript"] = new_lines
    
    # Update transcript_raw
    for item in transcript_data.get("transcript_raw", []):
        if item.get("speaker") in speaker_map:
            item["speaker"] = speaker_map[item["speaker"]]
    
    # Update speakers list
    new_speakers = [speaker_map.get(s, s) for s in speakers]
    transcript_data["speakers"] = new_speakers
    
    # Update stats
    if "stats" in transcript_data and "speakers" in transcript_data["stats"]:
        new_stats = {}
        for spk, data in transcript_data["stats"]["speakers"].items():
            new_spk = speaker_map.get(spk, spk)
            new_stats[new_spk] = data
        transcript_data["stats"]["speakers"] = new_stats
    
    # Update talk_ratios
    new_ratios = [replace_speaker(r) for r in transcript_data.get("talk_ratios", [])]
    transcript_data["talk_ratios"] = new_ratios
    
    # Store the mapping for reference
    transcript_data["speaker_mapping"] = speaker_map
    
    return transcript_data


def get_api_key():
    """Get AssemblyAI API key from Keychain or environment."""
    # Try macOS Keychain first
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "assemblyai", "-s", "assemblyai-api", "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    
    # Fall back to environment variable
    key = os.environ.get("ASSEMBLYAI_API_KEY", "")
    if not key:
        console.print("[red]Error: No AssemblyAI API key found.[/red]")
        console.print("Store in Keychain:")
        console.print('  security add-generic-password -a assemblyai -s assemblyai-api -w "YOUR_KEY"')
        console.print("Or set environment variable: export ASSEMBLYAI_API_KEY=YOUR_KEY")
        sys.exit(1)
    return key


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_duration(seconds: float) -> str:
    """Format duration for display."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"


def log_cost(audio_duration: float, filename: str):
    """Log transcription cost for tracking."""
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    cost = audio_duration * COST_PER_SECOND
    entry = {
        "date": datetime.now().isoformat(),
        "file": filename,
        "duration_seconds": audio_duration,
        "cost_usd": round(cost, 4),
    }
    
    if COST_LOG.exists():
        log = json.loads(COST_LOG.read_text())
    else:
        log = {"entries": [], "total_cost_usd": 0, "total_duration_seconds": 0}
    
    log["entries"].append(entry)
    log["total_cost_usd"] = round(log["total_cost_usd"] + cost, 4)
    log["total_duration_seconds"] = round(log["total_duration_seconds"] + audio_duration, 1)
    
    COST_LOG.write_text(json.dumps(log, indent=2))
    return cost


def save_backup(result: dict, audio_path: str):
    """Save local backup of transcript."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    basename = Path(audio_path).stem[:50]  # Truncate long names
    backup_path = TRANSCRIPTS_DIR / f"{timestamp}_{basename}.json"
    
    backup_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return backup_path


def notify_completion(title: str, duration: float, speakers: int, output_path: str = None):
    """Send completion notification via macOS."""
    message = f"Transcription complete: {title}"
    body = f"Duration: {format_duration(duration)} | Speakers: {speakers}"
    if output_path:
        body += f" | Saved to: {Path(output_path).name}"
    
    try:
        # Use terminal-notifier if available, fall back to osascript
        result = subprocess.run(["which", "terminal-notifier"], capture_output=True)
        if result.returncode == 0:
            subprocess.run([
                "terminal-notifier",
                "-title", "Meeting Transcriber",
                "-message", f"{message}\n{body}",
                "-sound", "Glass",
            ], capture_output=True, timeout=5)
        else:
            # Escape quotes for osascript
            safe_msg = message.replace('"', '\\"')
            safe_body = body.replace('"', '\\"')
            subprocess.run([
                "osascript", "-e",
                f'display notification "{safe_body}" with title "Meeting Transcriber" subtitle "{safe_msg}" sound name "Glass"'
            ], capture_output=True, timeout=5)
    except Exception:
        pass  # Best effort
    
    # Write trigger file for automation systems to pick up
    trigger_file = Path.home() / ".config" / "meeting-transcriber" / "last_completion.json"
    try:
        trigger_file.parent.mkdir(parents=True, exist_ok=True)
        trigger_file.write_text(json.dumps({
            "title": title,
            "duration": duration,
            "speakers": speakers,
            "output": output_path,
            "timestamp": datetime.now().isoformat(),
        }, indent=2))
    except Exception:
        pass


def transcribe_meeting(
    audio_path: str,
    speakers: int = None,
    context: str = None,
    names: list = None,
    verbose: bool = False,
    notify: bool = True,
) -> dict:
    """Transcribe and diarize audio using AssemblyAI with rich progress display."""
    
    api_key = get_api_key()
    aai.settings.api_key = api_key
    
    filename = Path(audio_path).name
    
    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    audio_duration = float(probe.stdout.strip()) if probe.stdout.strip() else 0
    duration_min = round(audio_duration / 60, 1)
    
    # Estimate cost
    est_cost = audio_duration * COST_PER_SECOND
    
    # Status display
    status_table = Table.grid(padding=(0, 2))
    status_table.add_column(style="cyan", justify="right")
    status_table.add_column(style="white")
    
    status_table.add_row("📁 File:", filename)
    status_table.add_row("⏱️  Duration:", f"{duration_min} min")
    status_table.add_row("💰 Est. Cost:", f"${est_cost:.2f}")
    status_table.add_row("👥 Speakers:", str(speakers) if speakers else "Auto-detect")
    
    console.print(Panel(status_table, title="[bold blue]Meeting Transcriber[/bold blue]", border_style="blue"))
    
    if verbose:
        console.print(f"[dim]API Key: {api_key[:8]}...{api_key[-4:]}[/dim]")
        console.print(f"[dim]Audio path: {audio_path}[/dim]")
    
    # Configure transcription
    config = aai.TranscriptionConfig(
        speech_models=["universal-3-pro"],
        speaker_labels=True,
        speakers_expected=speakers,
    )
    
    if verbose:
        console.print(f"[dim]Config: speech_models=universal-3-pro, speaker_labels=True, speakers_expected={speakers}[/dim]")
    
    # Progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        
        # Upload task
        upload_task = progress.add_task("[cyan]Uploading audio...", total=100)
        
        transcriber = aai.Transcriber()
        t0 = time.time()
        
        # Submit (includes upload)
        if verbose:
            console.print("[dim]Submitting to AssemblyAI...[/dim]")
        
        transcript = transcriber.submit(audio_path, config=config)
        progress.update(upload_task, completed=100, description="[green]✓ Uploaded")
        
        upload_time = time.time() - t0
        if verbose:
            console.print(f"[dim]Upload completed in {upload_time:.1f}s, transcript ID: {transcript.id}[/dim]")
        
        # Processing task
        process_task = progress.add_task("[cyan]Processing audio...", total=100)
        
        # Poll for completion
        poll_start = time.time()
        last_status = None
        
        while transcript.status not in [aai.TranscriptStatus.completed, aai.TranscriptStatus.error]:
            time.sleep(2)
            transcript = aai.Transcript.get_by_id(transcript.id)
            
            elapsed = time.time() - poll_start
            # Estimate progress (AssemblyAI typically takes 20-40% of audio duration)
            est_total = max(audio_duration * 0.1, 30)  # At least 30s estimate
            pct = min(95, (elapsed / est_total) * 100)
            
            status_text = {
                "queued": "[yellow]Queued...",
                "processing": "[cyan]Processing audio...",
            }.get(str(transcript.status), f"[cyan]{transcript.status}")
            
            progress.update(process_task, completed=pct, description=status_text)
            
            if verbose and transcript.status != last_status:
                console.print(f"[dim]Status: {transcript.status} (elapsed: {elapsed:.1f}s)[/dim]")
                last_status = transcript.status
        
        if transcript.status == aai.TranscriptStatus.error:
            progress.update(process_task, description="[red]✗ Failed")
            raise RuntimeError(f"Transcription failed: {transcript.error}")
        
        progress.update(process_task, completed=100, description="[green]✓ Transcribed")
        
        process_time = time.time() - t0
        if verbose:
            console.print(f"[dim]Processing completed in {process_time:.1f}s[/dim]")
        
        # Analysis task
        analysis_task = progress.add_task("[cyan]Analyzing results...", total=100)
        
        # Build output
        speakers_found = sorted(set(f"Speaker {u.speaker}" for u in transcript.utterances))
        
        transcript_lines = []
        transcript_raw = []
        speaker_time = {}
        speaker_turns = {}
        
        for utterance in transcript.utterances:
            speaker = f"Speaker {utterance.speaker}"
            start_sec = utterance.start / 1000
            end_sec = utterance.end / 1000
            text = utterance.text
            duration = end_sec - start_sec
            
            timestamp = format_timestamp(start_sec)
            transcript_lines.append(f"**{speaker}** [{timestamp}]: {text}")
            
            transcript_raw.append({
                "speaker": speaker,
                "start": start_sec,
                "end": end_sec,
                "text": text,
            })
            
            speaker_time[speaker] = speaker_time.get(speaker, 0) + duration
            speaker_turns[speaker] = speaker_turns.get(speaker, 0) + 1
        
        progress.update(analysis_task, completed=50)
        
        total_time = sum(speaker_time.values())
        stats = {"total_duration_seconds": total_time, "speakers": {}}
        talk_ratios = []
        
        for spk in speakers_found:
            talk_time = speaker_time.get(spk, 0)
            ratio = round(talk_time / total_time * 100, 1) if total_time > 0 else 0
            turns = speaker_turns.get(spk, 0)
            
            stats["speakers"][spk] = {
                "talk_time_seconds": round(talk_time, 1),
                "talk_ratio": ratio,
                "turns": turns,
            }
            talk_ratios.append(f"{spk}: {ratio}% ({turns} turns)")
        
        progress.update(analysis_task, completed=100, description="[green]✓ Analyzed")
    
    total_time_elapsed = time.time() - t0
    actual_cost = log_cost(audio_duration, filename)
    
    # Build result
    result = {
        "speakers": speakers_found,
        "duration_minutes": duration_min,
        "stats": stats,
        "talk_ratios": talk_ratios,
        "transcript": transcript_lines,
        "transcript_raw": transcript_raw,
        "full_text": transcript.text,
        "processing_time_seconds": round(total_time_elapsed, 1),
        "cost_usd": round(actual_cost, 4),
        "transcript_id": transcript.id,
    }
    
    if context:
        result["context"] = context
    
    # Apply speaker names from context or explicit names
    extracted_names = names or extract_names_from_context(context)
    if extracted_names:
        if verbose:
            console.print(f"[dim]Extracted names: {extracted_names}[/dim]")
        result = apply_speaker_names(result, extracted_names)
        if verbose:
            console.print(f"[dim]Speaker mapping: {result.get('speaker_mapping', {})}[/dim]")
    
    # Summary display
    console.print()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="green", justify="right")
    summary.add_column(style="white")
    
    summary.add_row("✅ Status:", "Complete")
    summary.add_row("⏱️  Processing:", f"{total_time_elapsed:.1f}s")
    summary.add_row("👥 Speakers:", str(len(speakers_found)))
    summary.add_row("💬 Exchanges:", str(len(transcript_raw)))
    summary.add_row("💰 Cost:", f"${actual_cost:.2f}")
    summary.add_row("📊 Talk ratios:", ", ".join(talk_ratios))
    
    console.print(Panel(summary, title="[bold green]Results[/bold green]", border_style="green"))
    
    # Notify
    if notify:
        notify_completion(filename, audio_duration, len(speakers_found))
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Meeting Transcriber (AssemblyAI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s meeting.m4a
  %(prog)s meeting.m4a --speakers 2 --output transcript.json
  %(prog)s meeting.m4a --verbose --no-notify
        """
    )
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--speakers", "-s", type=int, default=None,
                        help="Expected number of speakers (optional)")
    parser.add_argument("--context", "-c", type=str, default=None,
                        help="Meeting context (e.g., 'Interview with Sarah')")
    parser.add_argument("--names", "-n", type=str, default=None,
                        help="Speaker names, comma-separated (e.g., 'Sarah,James')")
    parser.add_argument("--output", "-o", default=None,
                        help="Output JSON file (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--no-notify", action="store_true",
                        help="Disable completion notification")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip local backup")
    
    args = parser.parse_args()
    
    if not Path(args.audio).exists():
        console.print(f"[red]Error: File not found: {args.audio}[/red]")
        sys.exit(1)
    
    # Parse names
    names = None
    if args.names:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
    
    try:
        result = transcribe_meeting(
            args.audio,
            speakers=args.speakers,
            context=args.context,
            names=names,
            verbose=args.verbose,
            notify=not args.no_notify,
        )
        
        # Save backup
        if not args.no_backup:
            backup_path = save_backup(result, args.audio)
            if args.verbose:
                console.print(f"[dim]Backup saved: {backup_path}[/dim]")
        
        # Output
        output_json = json.dumps(result, indent=2, ensure_ascii=False)
        
        if args.output:
            Path(args.output).write_text(output_json)
            console.print(f"\n[blue]Output saved to:[/blue] {args.output}")
        else:
            print(output_json)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
