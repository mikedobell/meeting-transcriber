#!/usr/bin/env python3
"""
Check for new audio files in the watch folder.
Returns JSON list of new files not yet processed.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Configuration - customize these paths
WATCH_FOLDER = Path.home() / "Transcribe"  # Where you drop audio files
PROCESSED_LOG = Path.home() / ".config" / "meeting-transcriber" / "processed_files.json"

# Audio extensions to look for
AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".ogg", ".aac", ".flac", ".mp4", ".webm"}


def load_processed():
    """Load list of already-processed files."""
    if PROCESSED_LOG.exists():
        return set(json.loads(PROCESSED_LOG.read_text()))
    return set()


def save_processed(processed: set):
    """Save list of processed files."""
    PROCESSED_LOG.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_LOG.write_text(json.dumps(list(processed), indent=2))


def mark_processed(filepath: str):
    """Mark a file as processed."""
    processed = load_processed()
    processed.add(filepath)
    save_processed(processed)


def check_for_new_files() -> list:
    """Check watch folder for new audio files."""
    if not WATCH_FOLDER.exists():
        return []
    
    processed = load_processed()
    new_files = []
    
    for f in WATCH_FOLDER.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
            filepath = str(f.resolve())
            if filepath not in processed:
                # Get file info
                stat = f.stat()
                new_files.append({
                    "path": filepath,
                    "name": f.name,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
    
    # Sort by modification time (newest first)
    new_files.sort(key=lambda x: x["modified"], reverse=True)
    
    return new_files


def main():
    new_files = check_for_new_files()
    
    if new_files:
        print(json.dumps(new_files, indent=2))
    else:
        print("[]")
    
    return len(new_files)


if __name__ == "__main__":
    exit(0 if main() == 0 else 0)  # Always exit 0, count is informational
