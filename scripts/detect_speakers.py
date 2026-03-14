#!/usr/bin/env python3
"""
Detect speaker names from transcript content.
Looks for:
- Filename patterns: "YYYY-MM-DD - Speaker Name.ext" or "Topic with Speaker Name.ext"
- Self-introductions: "I'm Sarah", "My name is John", "This is Mike"
- Direct addresses: "So Mike,", "Thanks Sarah", "Hey John"
- Questions to named person: "what do you think, Mike?"
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def extract_name_from_filename(filepath: str) -> Optional[str]:
    """
    Extract speaker name from filename patterns like:
    - "2024-02-20 - John Smith.m4a" → "John Smith"
    - "Call with Jamie Smith.m4a" → "Jamie Smith"
    - "Interview - Sarah Jones.m4a" → "Sarah Jones"
    """
    filename = Path(filepath).stem  # Remove extension
    
    # Pattern 1: "YYYY-MM-DD - Name"
    match = re.match(r'^\d{4}-\d{2}-\d{2}\s*-\s*(.+)$', filename)
    if match:
        return match.group(1).strip()
    
    # Pattern 2: "Something - Name"
    if ' - ' in filename:
        parts = filename.split(' - ')
        # Take the last part (likely the name)
        return parts[-1].strip()
    
    # Pattern 3: "with Name" or "and Name"
    for pattern in [r'\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 
                    r'\band\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']:
        match = re.search(pattern, filename)
        if match:
            return match.group(1).strip()
    
    return None


def find_name_mentions(text: str) -> list[tuple[str, str]]:
    """Find potential name mentions and their context."""
    mentions = []
    
    # Common first names to look for (more reliable than pattern matching)
    common_names = {
        'mike', 'michael', 'jamie', 'james', 'john', 'david', 'chris', 'christopher',
        'sarah', 'sara', 'jessica', 'jennifer', 'ashley', 'emily', 'emma',
        'matt', 'matthew', 'josh', 'joshua', 'ryan', 'brian', 'kevin', 'jason',
        'cathy', 'catherine', 'kathy', 'karen', 'lisa', 'laura', 'amy', 'anna',
        'steve', 'steven', 'scott', 'jeff', 'jeffrey', 'eric', 'mark', 'paul',
        'alex', 'andrew', 'adam', 'dan', 'daniel', 'tom', 'thomas', 'joe', 'joseph',
        'bob', 'robert', 'bill', 'william', 'jim', 'peter', 'nick', 'nicholas',
        'sam', 'samuel', 'ben', 'benjamin', 'jake', 'jacob', 'ethan', 'noah',
        'hannah', 'megan', 'rachel', 'rebecca', 'nicole', 'stephanie', 'heather',
        'varun', 'nisha', 'raj', 'ravi', 'priya', 'amit', 'ankit', 'remy',
        'jensen', 'guido', 'azita', 'wren', 'kristen', 'kristin',
    }
    
    # Words that look like names but aren't
    exclude_words = {
        'i', 'the', 'this', 'that', 'what', 'when', 'where', 'why', 'how',
        'yes', 'no', 'yeah', 'okay', 'ok', 'so', 'and', 'but', 'or', 'if',
        'well', 'like', 'just', 'really', 'actually', 'basically', 'obviously',
        'making', 'looking', 'going', 'doing', 'being', 'having', 'getting',
        'trying', 'coming', 'saying', 'thinking', 'working', 'talking',
    }
    
    text_lower = text.lower()
    
    patterns = [
        # Self-introduction patterns - must be followed by a known name
        (r"(?:I'm|I am|my name is|this is)\s+([A-Z][a-z]+)", "self_intro"),
        
        # Direct address: "Thanks, Mike" or "Hey Mike"
        (r"(?:thanks|thank you|hey|hi),?\s+([A-Z][a-z]+)", "greeting"),
        
        # Name at end of sentence with comma: "right, Mike?"
        (r",\s+([A-Z][a-z]+)\s*[.!?]?\s*$", "end_address"),
        
        # "you, [Name]" or "you [Name]" at end
        (r"you,?\s+([A-Z][a-z]+)\s*[.!?]?\s*$", "you_name"),
        
        # Explicit mention: "as [Name] said" or "like [Name] mentioned"
        (r"(?:as|like|what)\s+([A-Z][a-z]+)\s+(?:said|mentioned|noted|thinks)", "reference"),
    ]
    
    for pattern, context_type in patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            name = match.group(1)
            name_lower = name.lower()
            
            # Only accept if it's a known common name
            if name_lower in common_names and name_lower not in exclude_words:
                mentions.append((name.capitalize(), context_type))
    
    # Also look for standalone name mentions (known names appearing in text)
    for name in common_names:
        if name in exclude_words:
            continue
        # Look for the name with word boundaries
        pattern = r'\b' + name + r'\b'
        if re.search(pattern, text_lower):
            # Check it's actually used as a name (not part of another word)
            for match in re.finditer(pattern, text_lower):
                start = match.start()
                # Get surrounding context
                ctx_start = max(0, start - 20)
                ctx_end = min(len(text), start + len(name) + 20)
                context = text_lower[ctx_start:ctx_end]
                
                # If preceded by addressing words, it's likely a name
                if re.search(r'(?:hey|hi|thanks|thank|so|well|ok|okay),?\s*$', context[:start-ctx_start]):
                    mentions.append((name.capitalize(), "direct_address"))
                    break
    
    return mentions


def analyze_transcript_for_speakers(transcript_data: dict) -> dict:
    """
    Analyze transcript to detect speaker names from content.
    Returns dict with detected names and evidence.
    """
    speakers = transcript_data.get("speakers", [])
    transcript_raw = transcript_data.get("transcript_raw", [])
    
    # Track name mentions by speaker
    speaker_mentions = defaultdict(lambda: defaultdict(list))
    
    # Track names mentioned ABOUT each speaker (by other speakers)
    speaker_addressed_as = defaultdict(lambda: defaultdict(int))
    
    for i, item in enumerate(transcript_raw):
        speaker = item.get("speaker", "")
        text = item.get("text", "")
        
        mentions = find_name_mentions(text)
        
        for name, context_type in mentions:
            if context_type == "self_intro":
                # This speaker introduced themselves as this name
                speaker_mentions[speaker]["self_intro"].append(name)
            else:
                # This speaker addressed someone else by this name
                # So the OTHER speaker might be this name
                speaker_mentions[speaker]["addresses_other"].append(name)
                
                # Look at adjacent turns to guess who was addressed
                # If next turn is a different speaker, they might be the one addressed
                if i + 1 < len(transcript_raw):
                    next_speaker = transcript_raw[i + 1].get("speaker", "")
                    if next_speaker != speaker:
                        speaker_addressed_as[next_speaker][name] += 1
    
    # Build detection results
    results = {
        "speakers": speakers,
        "detections": {},
        "confidence": {},
        "evidence": {},
    }
    
    for speaker in speakers:
        # Check for self-introduction (highest confidence)
        self_intros = speaker_mentions[speaker].get("self_intro", [])
        if self_intros:
            # Most common self-intro
            name = max(set(self_intros), key=self_intros.count)
            results["detections"][speaker] = name
            results["confidence"][speaker] = "high"
            results["evidence"][speaker] = f"Self-introduced as '{name}'"
            continue
        
        # Check for being addressed by others
        addressed = speaker_addressed_as[speaker]
        if addressed:
            name = max(addressed, key=addressed.get)
            count = addressed[name]
            if count >= 2:
                results["detections"][speaker] = name
                results["confidence"][speaker] = "medium"
                results["evidence"][speaker] = f"Addressed as '{name}' {count} times"
            elif count == 1:
                results["detections"][speaker] = name
                results["confidence"][speaker] = "low"
                results["evidence"][speaker] = f"Possibly addressed as '{name}' once"
            continue
        
        # No detection
        results["detections"][speaker] = None
        results["confidence"][speaker] = "none"
        results["evidence"][speaker] = "No name detected in transcript"
    
    return results


def display_detection_results(results: dict, transcript_data: dict):
    """Display detection results in a nice table."""
    stats = transcript_data.get("stats", {}).get("speakers", {})
    
    console.print()
    console.print(Panel("[bold]Speaker Name Detection[/bold]", style="blue"))
    
    table = Table()
    table.add_column("Speaker ID", style="cyan")
    table.add_column("Talk %", justify="right")
    table.add_column("Detected Name", style="green")
    table.add_column("Confidence", style="yellow")
    table.add_column("Evidence")
    
    for speaker in results["speakers"]:
        talk_ratio = stats.get(speaker, {}).get("talk_ratio", 0)
        detected = results["detections"].get(speaker) or "[dim]Unknown[/dim]"
        confidence = results["confidence"].get(speaker, "none")
        evidence = results["evidence"].get(speaker, "")
        
        conf_style = {
            "high": "[green]HIGH[/green]",
            "medium": "[yellow]MEDIUM[/yellow]",
            "low": "[red]LOW[/red]",
            "none": "[dim]NONE[/dim]",
        }.get(confidence, confidence)
        
        table.add_row(
            speaker,
            f"{talk_ratio:.1f}%",
            str(detected),
            conf_style,
            evidence,
        )
    
    console.print(table)
    console.print()


def suggest_mapping(results: dict, context_names: list = None) -> dict:
    """
    Suggest a speaker mapping based on detections and context.
    Returns proposed mapping: {speaker_id: proposed_name}
    """
    mapping = {}
    detected_names = set()
    
    # First pass: apply high/medium confidence detections
    for speaker in results["speakers"]:
        confidence = results["confidence"].get(speaker, "none")
        detected = results["detections"].get(speaker)
        
        if detected and confidence in ("high", "medium"):
            mapping[speaker] = detected
            detected_names.add(detected.lower())
    
    # Second pass: apply context names to unassigned speakers
    if context_names:
        unassigned_speakers = [s for s in results["speakers"] if s not in mapping]
        unassigned_names = [n for n in context_names if n.lower() not in detected_names]
        
        for speaker, name in zip(unassigned_speakers, unassigned_names):
            mapping[speaker] = name
    
    # Third pass: apply low confidence detections if still unassigned
    for speaker in results["speakers"]:
        if speaker not in mapping:
            confidence = results["confidence"].get(speaker, "none")
            detected = results["detections"].get(speaker)
            
            if detected and confidence == "low":
                mapping[speaker] = detected
    
    return mapping


def extract_speaker_context(transcript_data: dict, min_sentences: int = 2) -> dict:
    """
    Extract sample sentences from each speaker for context-based identification.
    Returns dict: {speaker_id: [sentence1, sentence2, ...]}
    """
    transcript = transcript_data.get("transcript_raw", [])
    context = defaultdict(list)
    
    for entry in transcript:
        speaker = entry.get("speaker")
        text = entry.get("text", "").strip()
        
        if not speaker or not text or len(text) < 20:  # Skip very short utterances
            continue
        
        # Look for substantial sentences (>30 chars, ends with punctuation)
        sentences = re.split(r'[.!?]+\s+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30 and len(context[speaker]) < min_sentences * 2:
                context[speaker].append(sentence)
    
    # Trim to min_sentences for each speaker
    for speaker in context:
        context[speaker] = context[speaker][:min_sentences]
    
    return dict(context)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Detect speaker names from transcript content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s transcript.json
  %(prog)s transcript.json --audio-file "2024-02-20 - John Smith.m4a"
  %(prog)s transcript.json --names Sarah James
        """
    )
    parser.add_argument("transcript", help="Path to transcript JSON file")
    parser.add_argument("--audio-file", "-a", help="Original audio filename (for name extraction)")
    parser.add_argument("--names", "-n", nargs="*", default=[], 
                        help="Context names to help with detection")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output only JSON mapping")
    parser.add_argument("--context", "-c", action="store_true",
                        help="Show context sentences for each speaker")
    
    args = parser.parse_args()
    
    data = json.loads(Path(args.transcript).read_text())
    
    # Try to extract name from audio filename
    filename_name = None
    if args.audio_file:
        filename_name = extract_name_from_filename(args.audio_file)
        if filename_name and not args.json:
            console.print(f"[dim]Detected from filename: {filename_name}[/dim]")
    
    # Add filename name to context if found
    context_names = args.names.copy()
    if filename_name and filename_name not in context_names:
        context_names.append(filename_name)
    
    results = analyze_transcript_for_speakers(data)
    
    if not args.json:
        display_detection_results(results, data)
    
    # Show context sentences if requested or if no names detected
    if args.context or (not args.json and not any(results["detections"].values())):
        console.print(Panel("[bold]Speaker Context (for identification)[/bold]", style="cyan"))
        context = extract_speaker_context(data, min_sentences=2)
        for speaker in sorted(context.keys()):
            stats = data.get("stats", {}).get("speakers", {}).get(speaker, {})
            talk_ratio = stats.get("talk_ratio", 0)
            console.print(f"\n[bold]{speaker}[/bold] ({talk_ratio:.1f}% talk time):")
            for i, sentence in enumerate(context[speaker], 1):
                console.print(f"  {i}. \"{sentence}\"")
        console.print()
    
    mapping = suggest_mapping(results, context_names)
    
    if not args.json:
        console.print("[bold]Suggested Mapping:[/bold]")
        console.print()
        for speaker, name in mapping.items():
            console.print(f"  {speaker} → {name}")
        console.print()
    
    print(json.dumps(mapping))
