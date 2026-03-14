#!/usr/bin/env python3
"""
Combine AssemblyAI transcript with Hume prosody analysis.

Merges emotional data with transcript segments for enriched coaching analysis.
"""

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def align_prosody_to_transcript(
    transcript_data: dict,
    prosody_data: dict,
    time_tolerance: float = 2.0,
) -> dict:
    """
    Align Hume prosody predictions with AssemblyAI transcript segments.
    
    Uses timestamp matching with tolerance for slight differences.
    """
    transcript_raw = transcript_data.get("transcript_raw", [])
    prosody_preds = prosody_data.get("predictions", [])
    
    # Build a map of prosody predictions by time range
    prosody_by_time = []
    for pred in prosody_preds:
        prosody_by_time.append({
            "begin": pred.get("begin", 0),
            "end": pred.get("end", 0),
            "emotions": pred.get("emotions", {}),
            "top_emotions": pred.get("top_emotions", []),
            "speaker": pred.get("speaker", "unknown"),
        })
    
    # Sort by begin time
    prosody_by_time.sort(key=lambda x: x["begin"])
    
    # Match transcript segments to prosody
    enriched_segments = []
    
    for seg in transcript_raw:
        seg_start = seg.get("start", 0)
        seg_end = seg.get("end", 0)
        
        # Find overlapping prosody predictions
        matching_prosody = []
        for pros in prosody_by_time:
            # Check for overlap
            if pros["end"] >= seg_start - time_tolerance and pros["begin"] <= seg_end + time_tolerance:
                matching_prosody.append(pros)
        
        # Aggregate emotions from matching predictions
        if matching_prosody:
            aggregated_emotions = {}
            for mp in matching_prosody:
                for emo, score in mp["emotions"].items():
                    if emo not in aggregated_emotions:
                        aggregated_emotions[emo] = []
                    aggregated_emotions[emo].append(score)
            
            # Average the scores
            avg_emotions = {
                emo: round(sum(scores) / len(scores), 3)
                for emo, scores in aggregated_emotions.items()
            }
            
            # Get top emotions
            sorted_emotions = sorted(avg_emotions.items(), key=lambda x: x[1], reverse=True)
            top_emotions = [{"name": name, "score": score} for name, score in sorted_emotions[:5]]
        else:
            avg_emotions = {}
            top_emotions = []
        
        enriched = {
            **seg,
            "prosody": {
                "emotions": avg_emotions,
                "top_emotions": top_emotions,
                "matched_segments": len(matching_prosody),
            }
        }
        enriched_segments.append(enriched)
    
    return {
        **transcript_data,
        "transcript_enriched": enriched_segments,
        "prosody_summary": prosody_data.get("speaker_summaries", {}),
        "prosody_job_id": prosody_data.get("job_id", ""),
    }


def generate_coaching_context(enriched_data: dict, user_speaker: str = None) -> str:
    """
    Generate a coaching context block for LLM analysis.
    
    This summarizes the prosody data in a format suitable for coaching prompts.
    """
    lines = ["## Audio Sentiment Analysis (from Hume AI)\n"]
    
    # Speaker emotional profiles
    prosody_summary = enriched_data.get("prosody_summary", {})
    
    if prosody_summary:
        lines.append("### Speaker Emotional Profiles\n")
        
        for speaker, data in prosody_summary.items():
            speaker_label = "User" if speaker == user_speaker else speaker
            lines.append(f"**{speaker_label}** (average across all utterances):")
            
            top_emotions = data.get("top_emotions", [])
            if top_emotions:
                emotion_str = ", ".join([f"{e['name']}: {e['score']:.2f}" for e in top_emotions[:8]])
                lines.append(f"- Top emotions: {emotion_str}")
            
            # Highlight concerning patterns
            avgs = data.get("emotion_averages", {})
            
            concerns = []
            if avgs.get("Anxiety", 0) > 0.3:
                concerns.append(f"elevated anxiety ({avgs['Anxiety']:.2f})")
            if avgs.get("Doubt", 0) > 0.3:
                concerns.append(f"significant doubt ({avgs['Doubt']:.2f})")
            if avgs.get("Distress", 0) > 0.3:
                concerns.append(f"notable distress ({avgs['Distress']:.2f})")
            
            if concerns and speaker == user_speaker:
                lines.append(f"- ⚠️ Patterns of concern: {', '.join(concerns)}")
            
            strengths = []
            if avgs.get("Determination", 0) > 0.3:
                strengths.append(f"strong determination ({avgs['Determination']:.2f})")
            if avgs.get("Concentration", 0) > 0.3:
                strengths.append(f"good concentration ({avgs['Concentration']:.2f})")
            if avgs.get("Calmness", 0) > 0.3:
                strengths.append(f"calm demeanor ({avgs['Calmness']:.2f})")
            
            if strengths and speaker == user_speaker:
                lines.append(f"- ✅ Strengths: {', '.join(strengths)}")
            
            lines.append("")
    
    # Notable moments
    enriched_segments = enriched_data.get("transcript_enriched", [])
    
    notable = []
    for seg in enriched_segments:
        if seg.get("speaker") != user_speaker:
            continue
            
        emotions = seg.get("prosody", {}).get("emotions", {})
        if not emotions:
            continue
        
        # High anxiety
        if emotions.get("Anxiety", 0) > 0.5:
            notable.append({
                "time": seg.get("start", 0),
                "type": "High Anxiety",
                "score": emotions["Anxiety"],
                "text": seg.get("text", "")[:80],
            })
        
        # Low confidence signals
        if emotions.get("Doubt", 0) > 0.45 and emotions.get("Distress", 0) > 0.3:
            notable.append({
                "time": seg.get("start", 0),
                "type": "Low Confidence",
                "doubt": emotions["Doubt"],
                "text": seg.get("text", "")[:80],
            })
        
        # Strong positive
        if emotions.get("Determination", 0) > 0.5 or emotions.get("Triumph", 0) > 0.4:
            notable.append({
                "time": seg.get("start", 0),
                "type": "Strong/Confident",
                "score": max(emotions.get("Determination", 0), emotions.get("Triumph", 0)),
                "text": seg.get("text", "")[:80],
            })
    
    if notable:
        lines.append("### Notable Emotional Moments\n")
        for moment in notable[:10]:  # Limit to 10 most notable
            time_str = f"{int(moment['time']//60):02d}:{int(moment['time']%60):02d}"
            lines.append(f"- **[{time_str}] {moment['type']}**: \"{moment['text']}...\"")
        lines.append("")
    
    lines.append("""
### Coaching Notes on Audio Sentiment

When analyzing performance, consider:
1. **Words vs. Tone Mismatches**: Where does prosody contradict words? (e.g., confident words with anxious tone)
2. **Emotional Regulation**: How well is composure maintained during challenging moments?
3. **Authentic Confidence**: Is confidence coming through in tone, or just word choice?
4. **Engagement Signals**: Interest, concentration, and excitement levels during key discussions
5. **Stress Response**: How does the emotional profile shift when discussing difficult topics?

Use this data to provide specific, timestamp-referenced coaching feedback.
""")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Combine transcript with prosody analysis"
    )
    parser.add_argument("transcript", help="AssemblyAI transcript JSON file")
    parser.add_argument("prosody", help="Hume prosody analysis JSON file")
    parser.add_argument("--output", "-o", help="Output combined JSON file")
    parser.add_argument("--user-speaker", help="Speaker ID for the user being coached")
    parser.add_argument("--coaching-context", action="store_true",
                        help="Generate coaching context block")
    parser.add_argument("--context-output", help="Output file for coaching context (markdown)")
    
    args = parser.parse_args()
    
    # Load data
    transcript_data = json.loads(Path(args.transcript).read_text())
    prosody_data = json.loads(Path(args.prosody).read_text())
    
    # Combine
    combined = align_prosody_to_transcript(transcript_data, prosody_data)
    
    # Detect user's speaker if not provided
    user_speaker = args.user_speaker
    if not user_speaker:
        # Try to match speaker labels between the two systems
        transcript_speakers = transcript_data.get("speakers", [])
        prosody_speakers = list(prosody_data.get("speaker_summaries", {}).keys())
        
        # Assume user is the first speaker
        if transcript_speakers:
            user_speaker = transcript_speakers[0]
        elif prosody_speakers:
            user_speaker = prosody_speakers[0]
    
    combined["user_speaker_id"] = user_speaker
    
    # Output combined data
    if args.output:
        Path(args.output).write_text(json.dumps(combined, indent=2, ensure_ascii=False))
        console.print(f"[green]Combined data saved to:[/green] {args.output}")
    else:
        print(json.dumps(combined, indent=2, ensure_ascii=False))
    
    # Generate coaching context
    if args.coaching_context or args.context_output:
        coaching_ctx = generate_coaching_context(combined, user_speaker)
        
        if args.context_output:
            Path(args.context_output).write_text(coaching_ctx)
            console.print(f"[green]Coaching context saved to:[/green] {args.context_output}")
        elif args.coaching_context:
            print("\n" + "="*60)
            print(coaching_ctx)


if __name__ == "__main__":
    main()
