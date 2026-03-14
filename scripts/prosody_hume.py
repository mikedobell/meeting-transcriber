#!/usr/bin/env python3
"""
Hume AI Expression Measurement — Speech Prosody Analysis

Analyzes audio for emotional expression using Hume's prosody model.
Returns 48 emotional dimensions per utterance/sentence.

Requires:
    pip install hume

API Key:
    security add-generic-password -a hume -s hume-api -w "YOUR_KEY"
    
    Or: export HUME_API_KEY="YOUR_KEY"
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from hume import HumeClient
    from hume.expression_measurement.batch.types import InferenceBaseRequest, Models, Prosody
except ImportError:
    print("Error: hume package not installed. Run: pip install hume", file=sys.stderr)
    sys.exit(1)

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

console = Console()

# Key emotions for coaching context
COACHING_EMOTIONS = [
    "Anxiety",
    "Calmness", 
    "Concentration",
    "Confusion",
    "Contempt",
    "Determination",
    "Disappointment",
    "Distress",
    "Doubt",
    "Embarrassment",
    "Excitement",
    "Interest",
    "Joy",
    "Pride",
    "Sadness",
    "Satisfaction",
    "Shame",
    "Surprise (negative)",
    "Surprise (positive)",
    "Tiredness",
    "Triumph",
]


def get_api_key() -> str:
    """Get Hume API key from Keychain or environment."""
    # Try macOS Keychain first
    result = subprocess.run(
        ["security", "find-generic-password", "-a", "hume", "-s", "hume-api", "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    
    # Fall back to environment variable
    key = os.environ.get("HUME_API_KEY", "")
    if not key:
        console.print("[red]Error: No Hume API key found.[/red]")
        console.print("Store in Keychain:")
        console.print('  security add-generic-password -a hume -s hume-api -w "YOUR_KEY"')
        console.print("Or set environment variable: export HUME_API_KEY=YOUR_KEY")
        sys.exit(1)
    return key


def analyze_prosody(
    audio_path: str,
    granularity: str = "sentence",
    identify_speakers: bool = True,
    verbose: bool = False,
) -> dict:
    """
    Analyze speech prosody using Hume's Expression Measurement API.
    
    Args:
        audio_path: Path to audio file
        granularity: 'word', 'sentence', 'utterance', or 'conversational_turn'
        identify_speakers: Enable speaker diarization
        verbose: Print debug info
        
    Returns:
        Dict with prosody analysis results
    """
    api_key = get_api_key()
    client = HumeClient(api_key=api_key)
    
    filename = Path(audio_path).name
    
    # Status display
    status_table = Table.grid(padding=(0, 2))
    status_table.add_column(style="cyan", justify="right")
    status_table.add_column(style="white")
    status_table.add_row("📁 File:", filename)
    status_table.add_row("🎯 Granularity:", granularity)
    status_table.add_row("👥 Speaker ID:", "Yes" if identify_speakers else "No")
    
    console.print(Panel(status_table, title="[bold magenta]Hume Prosody Analysis[/bold magenta]", border_style="magenta"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        
        # Submit job
        task = progress.add_task("[cyan]Submitting to Hume...", total=None)
        
        t0 = time.time()
        
        # Read file and submit
        with open(audio_path, "rb") as f:
            inference_request = InferenceBaseRequest(
                models=Models(
                    prosody=Prosody(
                        granularity=granularity,
                        identify_speakers=identify_speakers,
                    )
                )
            )
            job = client.expression_measurement.batch.start_inference_job_from_local_file(
                file=[f],
                json=inference_request,
            )
        
        job_id = job
        if verbose:
            console.print(f"[dim]Job submitted: {job_id}[/dim]")
        
        progress.update(task, description="[cyan]Processing audio...")
        
        # Poll for completion
        while True:
            job_details = client.expression_measurement.batch.get_job_details(id=job_id)
            status = job_details.state.status
            
            if verbose:
                console.print(f"[dim]Status: {status}[/dim]")
            
            if status == "COMPLETED":
                break
            elif status == "FAILED":
                error = getattr(job_details.state, 'message', 'Unknown error')
                raise RuntimeError(f"Hume job failed: {error}")
            
            time.sleep(2)
        
        progress.update(task, description="[green]✓ Analysis complete")
        
        # Get predictions
        predictions = client.expression_measurement.batch.get_job_predictions(id=job_id)
        
        processing_time = time.time() - t0
    
    # Parse results
    results = {
        "job_id": job_id,
        "processing_time_seconds": round(processing_time, 1),
        "granularity": granularity,
        "predictions": [],
        "speaker_summaries": {},
    }
    
    # Process predictions
    for prediction in predictions:
        if hasattr(prediction, 'results') and prediction.results:
            for result in prediction.results:
                if hasattr(result, 'predictions') and result.predictions:
                    for pred_group in result.predictions:
                        if hasattr(pred_group, 'models') and pred_group.models:
                            prosody_result = getattr(pred_group.models, 'prosody', None)
                            if prosody_result and hasattr(prosody_result, 'grouped_predictions'):
                                for group in prosody_result.grouped_predictions:
                                    speaker = getattr(group, 'id', 'unknown')
                                    
                                    for pred in group.predictions:
                                        # Extract emotions
                                        emotions = {}
                                        if hasattr(pred, 'emotions'):
                                            for emotion in pred.emotions:
                                                emotions[emotion.name] = round(emotion.score, 3)
                                        
                                        # Get time info
                                        time_info = getattr(pred, 'time', {})
                                        begin = getattr(time_info, 'begin', 0)
                                        end = getattr(time_info, 'end', 0)
                                        
                                        entry = {
                                            "speaker": speaker,
                                            "text": getattr(pred, 'text', ''),
                                            "begin": begin,
                                            "end": end,
                                            "emotions": emotions,
                                            "top_emotions": get_top_emotions(emotions, n=5),
                                        }
                                        results["predictions"].append(entry)
                                        
                                        # Aggregate by speaker
                                        if speaker not in results["speaker_summaries"]:
                                            results["speaker_summaries"][speaker] = {
                                                "emotion_totals": {},
                                                "count": 0,
                                            }
                                        
                                        results["speaker_summaries"][speaker]["count"] += 1
                                        for emo, score in emotions.items():
                                            if emo not in results["speaker_summaries"][speaker]["emotion_totals"]:
                                                results["speaker_summaries"][speaker]["emotion_totals"][emo] = 0
                                            results["speaker_summaries"][speaker]["emotion_totals"][emo] += score
    
    # Compute speaker averages
    for speaker, data in results["speaker_summaries"].items():
        count = data["count"]
        if count > 0:
            averages = {k: round(v / count, 3) for k, v in data["emotion_totals"].items()}
            data["emotion_averages"] = averages
            data["top_emotions"] = get_top_emotions(averages, n=10)
            del data["emotion_totals"]
    
    # Summary display
    console.print()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="green", justify="right")
    summary.add_column(style="white")
    summary.add_row("✅ Status:", "Complete")
    summary.add_row("⏱️  Processing:", f"{processing_time:.1f}s")
    summary.add_row("🎤 Segments:", str(len(results["predictions"])))
    summary.add_row("👥 Speakers:", str(len(results["speaker_summaries"])))
    
    console.print(Panel(summary, title="[bold green]Prosody Results[/bold green]", border_style="green"))
    
    return results


def get_top_emotions(emotions: dict, n: int = 5) -> list:
    """Get top N emotions by score."""
    sorted_emotions = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
    return [{"name": name, "score": score} for name, score in sorted_emotions[:n]]


def extract_coaching_insights(results: dict, user_speaker: str = None) -> dict:
    """
    Extract coaching-relevant insights from prosody data.
    
    Args:
        results: Prosody analysis results
        user_speaker: Speaker ID for the user being coached
    """
    insights = {
        "overall_emotional_profile": {},
        "emotional_patterns": [],
        "notable_moments": [],
        "speaker_comparison": {},
    }
    
    # Find user's speaker ID if not provided
    if not user_speaker and results["speaker_summaries"]:
        # Default to first speaker
        user_speaker = list(results["speaker_summaries"].keys())[0]
    
    # Get user's emotional profile
    if user_speaker and user_speaker in results["speaker_summaries"]:
        user_data = results["speaker_summaries"][user_speaker]
        insights["overall_emotional_profile"] = user_data.get("emotion_averages", {})
        
        # Filter to coaching-relevant emotions
        coaching_relevant = {
            k: v for k, v in insights["overall_emotional_profile"].items()
            if k in COACHING_EMOTIONS
        }
        insights["coaching_emotions"] = coaching_relevant
    
    # Find notable emotional moments
    for pred in results["predictions"]:
        if pred.get("speaker") == user_speaker:
            emotions = pred.get("emotions", {})
            
            # High anxiety moments
            if emotions.get("Anxiety", 0) > 0.5:
                insights["notable_moments"].append({
                    "time": pred["begin"],
                    "type": "high_anxiety",
                    "score": emotions["Anxiety"],
                    "text": pred.get("text", "")[:100],
                })
            
            # Low confidence (high doubt + distress)
            if emotions.get("Doubt", 0) > 0.4 or emotions.get("Distress", 0) > 0.4:
                insights["notable_moments"].append({
                    "time": pred["begin"],
                    "type": "low_confidence",
                    "doubt": emotions.get("Doubt", 0),
                    "distress": emotions.get("Distress", 0),
                    "text": pred.get("text", "")[:100],
                })
            
            # Strong positive moments
            if emotions.get("Determination", 0) > 0.5 or emotions.get("Excitement", 0) > 0.5:
                insights["notable_moments"].append({
                    "time": pred["begin"],
                    "type": "strong_positive",
                    "determination": emotions.get("Determination", 0),
                    "excitement": emotions.get("Excitement", 0),
                    "text": pred.get("text", "")[:100],
                })
    
    return insights


def main():
    parser = argparse.ArgumentParser(
        description="Analyze speech prosody using Hume AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--granularity", "-g", default="sentence",
                        choices=["word", "sentence", "utterance", "conversational_turn"],
                        help="Analysis granularity (default: sentence)")
    parser.add_argument("--no-speakers", action="store_true",
                        help="Disable speaker identification")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--insights", action="store_true",
                        help="Include coaching insights in output")
    parser.add_argument("--user-speaker", help="Speaker ID for the user being coached")
    parser.add_argument("--verbose", "-v", action="store_true")
    
    args = parser.parse_args()
    
    if not Path(args.audio).exists():
        console.print(f"[red]Error: File not found: {args.audio}[/red]")
        sys.exit(1)
    
    try:
        results = analyze_prosody(
            args.audio,
            granularity=args.granularity,
            identify_speakers=not args.no_speakers,
            verbose=args.verbose,
        )
        
        if args.insights:
            results["coaching_insights"] = extract_coaching_insights(
                results, user_speaker=args.user_speaker
            )
        
        output_json = json.dumps(results, indent=2, ensure_ascii=False)
        
        if args.output:
            Path(args.output).write_text(output_json)
            console.print(f"\n[blue]Output saved to:[/blue] {args.output}")
        else:
            print(output_json)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
