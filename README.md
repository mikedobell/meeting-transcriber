# Meeting Transcriber

Cloud-based meeting transcription with speaker diarization, speaker name detection, emotional prosody analysis, and structured output to Notion.

## Features

- **Fast Cloud Transcription** — AssemblyAI's Universal-3-Pro model (~10s processing per minute of audio)
- **Speaker Diarization** — Automatic speaker separation with talk-time ratios
- **Speaker Name Detection** — Auto-detect names from self-introductions and direct addresses
- **Emotional Prosody Analysis** — Optional Hume AI integration for 48-dimension emotional analysis
- **Notion Publishing** — Structured meeting pages with summaries, action items, and transcripts
- **Email Summaries** — Send formatted summaries via Gmail (using gog CLI)
- **Professional Coaching** — Competency assessment framework for meeting analysis
- **Cost Tracking** — Track transcription costs over time

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API keys (see Configuration below)
# Then transcribe:
python scripts/transcribe_aai.py meeting.m4a --output transcript.json
```

## Configuration

### API Keys

**AssemblyAI** (required):
```bash
# macOS Keychain
security add-generic-password -a assemblyai -s assemblyai-api -w "YOUR_KEY"

# Or environment variable
export ASSEMBLYAI_API_KEY="YOUR_KEY"
```
Get a key at: https://www.assemblyai.com/app/account

**Hume AI** (optional, for prosody analysis):
```bash
security add-generic-password -a hume -s hume-api -w "YOUR_KEY"
```
Get a key at: https://app.hume.ai/settings/api-keys

**Notion** (optional, for publishing):
```bash
mkdir -p ~/.config/notion
echo "YOUR_NOTION_API_KEY" > ~/.config/notion/api_key
```

### Notion Setup

1. Create a [Notion integration](https://www.notion.so/my-integrations)
2. Share a parent page with your integration
3. Update `PARENT_PAGE_ID` in `scripts/notion_publish_simple.py`

### Email Setup (gog CLI)

For email summaries, install and configure [gog](https://github.com/google/gog):
```bash
npm install -g gog
gog auth
```

## Usage

### Basic Transcription

```bash
python scripts/transcribe_aai.py meeting.m4a --output transcript.json
```

Options:
- `--speakers N` — Expected number of speakers
- `--names "Alice,Bob"` — Speaker names (comma-separated)
- `--verbose` — Show debug output
- `--no-notify` — Disable completion notification

### Detect Speaker Names

```bash
python scripts/detect_speakers.py transcript.json --context
```

This analyzes the transcript for:
- Self-introductions ("I'm Sarah", "My name is John")
- Direct addresses ("Thanks, Mike", "Hey Sarah")
- Filename patterns ("2024-01-15 - Client Name.m4a")

### Prosody Analysis (Optional)

For emotional/tonal analysis:

```bash
# Analyze prosody
python scripts/prosody_hume.py meeting.m4a --output prosody.json --insights

# Combine with transcript
python scripts/combine_prosody.py transcript.json prosody.json \
  --output combined.json \
  --coaching-context \
  --context-output coaching_notes.md
```

### Publish to Notion

```bash
python scripts/notion_publish_simple.py \
  "Meeting Title" \
  "2024-01-15" \
  analysis.json \
  transcript.json
```

### Send Email Summary

```bash
python scripts/email_summary.py \
  "Meeting Title" \
  "2024-01-15" \
  analysis.json \
  transcript.json \
  --notion-url "https://notion.so/..." \
  --to recipient@example.com
```

### Full Pipeline

```bash
python scripts/full_pipeline.py meeting.m4a "Meeting with Sarah" \
  --title "Q4 Planning Discussion" \
  --email
```

### View Costs

```bash
python scripts/costs.py
```

## Analysis JSON Structure

The analysis step (typically done by an LLM) should produce JSON like:

```json
{
  "summary": "Executive summary of the meeting",
  "desired_outcome": "What the meeting aimed to achieve",
  "action_items": [
    {"owner": "Alice", "action": "Send proposal", "due": "Friday"}
  ],
  "decisions": ["Approved Q4 budget"],
  "discussion_topics": [
    {"title": "Budget Review", "summary": "Discussed Q4 allocations..."}
  ],
  "parking_lot": ["Revisit hiring plan next month"],
  "meeting_type": "Team Meeting",
  
  "professional_coaching": {
    "overall_assessment": "Strong facilitation with clear action items",
    "strengths": ["Kept discussion focused", "Good time management"],
    "growth_areas": ["Could delegate more action items"],
    "competencies": {
      "strategic_thinking": {
        "observed": true,
        "rating": "strong",
        "notes": "Connected budget decisions to Q1 goals"
      }
    },
    "recommendations": ["Consider time-boxing agenda items"]
  }
}
```

### Competency Ratings

- `strong` (🟢) — Demonstrated clearly and effectively
- `developing` (🟡) — Present but needs refinement
- `not_observed` (⚪) — Not relevant or not demonstrated

### Competencies Tracked

1. Strategic thinking & vision
2. Executive presence
3. Stakeholder management
4. Leading through ambiguity
5. Emotional intelligence
6. Decision-making
7. Delegation & accountability

See `references/competency-rubric.md` for detailed assessment guidelines.

## File Locations

| Path | Purpose |
|------|---------|
| `~/.config/meeting-transcriber/transcripts/` | Local transcript backups |
| `~/.config/meeting-transcriber/cost_log.json` | Cost tracking |
| `~/.config/meeting-transcriber/processed_files.json` | Processed file list |

## Costs

- **AssemblyAI**: ~$0.015/minute (free tier: 5 hours/month)
- **Hume AI**: ~$0.006/minute (free tier: 200 requests/day)

A 45-minute meeting costs ~$1.00 with both services.

## Requirements

- Python 3.10+
- ffmpeg (for audio duration detection)
- macOS Keychain (for secure credential storage) or environment variables

## License

MIT
