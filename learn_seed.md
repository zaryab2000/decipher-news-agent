---
description: "Transform a YouTube tutorial into a deep, structured, replicable guide saved locally. Usage: /learn <youtube-url>"
---

# /learn — YouTube Tutorial Deep-Learner

Transform a YouTube tutorial video into a comprehensive, step-by-step guide saved as a local markdown file. Unlike `/summarize`, this command produces a document optimized for both human understanding and AI-agent replication — not a summary, but a complete instructional document.

## Step 1: Parse Input & Load Config

The input is: `$ARGUMENTS`

If the input is empty, print this usage message and stop:
```
Usage: /learn <youtube-url>

Examples:
  /learn https://www.youtube.com/watch?v=VIDEO_ID
  /learn https://youtu.be/VIDEO_ID

This command accepts only direct YouTube URLs (not playlist positions).
It is designed for tutorial videos — walkthroughs, how-to guides, system explanations.
```

Validate the input:
- If the input contains `youtube.com` or `youtu.be`: proceed.
- Otherwise: print `"Invalid argument. /learn only accepts YouTube URLs. Playlist positions are not supported."` and stop.

Source environment variables:
```bash
set -a && source .env && set +a
```

Read `dna-config.yaml` from the project root.

## Step 2: Resolve Video Metadata

Extract the video ID from the URL and fetch metadata via YouTube Data API v3:

```bash
uv run python3 -c "
import json, os, sys, re
import requests

url = sys.argv[1]

# Extract video ID
vid = None
patterns = [
    r'(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
]
for p in patterns:
    m = re.search(p, url)
    if m:
        vid = m.group(1)
        break
if not vid:
    print(f'Error: Could not extract video ID from URL: {url}', file=sys.stderr)
    sys.exit(1)

# Refresh OAuth token
resp = requests.post('https://oauth2.googleapis.com/token', data={
    'client_id': os.environ['GOOGLE_CLIENT_ID'],
    'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
    'refresh_token': os.environ['GOOGLE_REFRESH_TOKEN'],
    'grant_type': 'refresh_token'
}, timeout=15)
if resp.status_code != 200:
    print(f'Token refresh failed: {resp.status_code} {resp.text}', file=sys.stderr)
    sys.exit(1)
token = resp.json()['access_token']

# Fetch video metadata
r = requests.get('https://www.googleapis.com/youtube/v3/videos',
                  params={'part': 'snippet,contentDetails', 'id': vid},
                  headers={'Authorization': f'Bearer {token}'}, timeout=15)
if r.status_code != 200:
    print(f'Video fetch failed: {r.status_code} {r.text}', file=sys.stderr)
    sys.exit(1)

items = r.json().get('items', [])
if not items:
    print(f'Error: Video not found: {vid}', file=sys.stderr)
    sys.exit(1)

item = items[0]
iso = item['contentDetails']['duration']
m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso)
duration = ''
if m:
    h, mn, s = int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0)
    duration = f'{h}:{mn:02d}:{s:02d}' if h else f'{mn}:{s:02d}'

json.dump({
    'video_id': vid, 'title': item['snippet']['title'],
    'channel': item['snippet']['channelTitle'], 'duration': duration,
    'url': f'https://www.youtube.com/watch?v={vid}'
}, sys.stdout)
" "YOUTUBE_URL"
```

Replace `YOUTUBE_URL` with the user's input URL. Parse the JSON output and store `video_id`, `title`, `channel`, `duration`, and `url`.

## Step 3: Extract Full Transcript

Using the video ID from Step 2, extract the transcript via `youtube-transcript-api`:

```bash
uv run python3 -c "
import sys
from youtube_transcript_api import YouTubeTranscriptApi

video_id = sys.argv[1]
try:
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id, languages=['en'])
except Exception as e:
    print(f'Transcript fetch failed: {e}', file=sys.stderr)
    sys.exit(1)

full_text = ' '.join(entry.text for entry in transcript)
print(full_text)
" "VIDEO_ID"
```

Replace `VIDEO_ID` with the actual video ID. Use a timeout of 30000ms.

Capture the stdout as the raw transcript text.

### Fallback: yt-dlp

If `youtube-transcript-api` fails (exits non-zero), fall back to `yt-dlp`:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download --write-sub \
  -o "/tmp/dna-%(id)s" "VIDEO_URL" 2>/dev/null
```

Then strip timestamps from the resulting subtitle file:

```bash
uv run python3 -c "
import sys, re, os

video_id = sys.argv[1]
vtt_path = f'/tmp/dna-{video_id}.en.vtt'
srt_path = f'/tmp/dna-{video_id}.en.srt'

path = vtt_path if os.path.exists(vtt_path) else srt_path
if not os.path.exists(path):
    print('Error: No subtitle file found.', file=sys.stderr)
    sys.exit(1)

with open(path) as f:
    content = f.read()

lines = []
for line in content.splitlines():
    if re.match(r'^\d{2}:\d{2}', line):
        continue
    if re.match(r'^\d+$', line.strip()):
        continue
    if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
        continue
    cleaned = re.sub(r'<[^>]+>', '', line).strip()
    if cleaned:
        lines.append(cleaned)

deduped = []
for line in lines:
    if not deduped or line != deduped[-1]:
        deduped.append(line)

print(' '.join(deduped))
" "VIDEO_ID"
```

### Both methods fail

If both `youtube-transcript-api` and `yt-dlp` fail to produce a transcript, print:
```
Error: Could not extract transcript for this video. The video may not have captions available.
/learn requires a transcript to produce a guide — cannot proceed without one.
```
Stop execution. Do NOT create any file without a transcript.

### Long videos

If the transcript output exceeds 30,000 characters, write it to `/tmp/dna-transcript-VIDEO_ID.txt` first, then read it with the Read tool.

## Step 4: Generate Tutorial Document

You now have the full transcript. Read it deeply and completely — do not skim. Your goal is to understand the tutorial as thoroughly as a practitioner who watched it twice.

Produce a comprehensive tutorial document following this exact structure. Every section is mandatory. Do not abbreviate, truncate, or use placeholder text. This document must be complete enough for an AI agent to replicate the entire tutorial from scratch without watching the video.

---

Compute today's date in GST (GMT+4) in DD/MM/YY format.

Classify the tutorial type. Choose the most accurate from:
- `tool walkthrough` — how to use a specific tool or software
- `concept explainer` — teaching a concept, framework, or mental model
- `system design` — how someone built or architected a system
- `workflow / process` — a creator's or practitioner's working method
- `code tutorial` — writing code to build something specific
- `other` — if none of the above fit, describe it in 2-3 words

---

The document written to disk must use this template (write it literally as markdown, with real markdown code fences using backticks):

Section headers and content follow this pattern:

# [Video Title]

blockquote with: Channel, Duration, Source URL, Learned on date, Tutorial type

---

## Overview
2-4 substantial paragraphs: what it teaches, why it matters, who it is for, what problem it solves.

---

## Prerequisites

### Knowledge Required
- bullet list of required knowledge

### Tools & Software Required
table with columns: Tool | Version (if mentioned) | Install Command / Source

---

## Core Concepts
One subsection per concept (skip if tutorial has none):

### [Concept Name]
**What it is:** definition
**Why it matters here:** how used in the tutorial

---

## Step-by-Step Tutorial

One subsection per step in chronological order:

### Step 1: [name]
**What this achieves:** one sentence
**How it works:** thorough explanation of the mechanism
**How it fits into the overall system:** connection to before/after
**Commands / Code / Actions:** code block with exact commands/code
**Notes / Pitfalls:** warnings or "None mentioned."

Repeat for all steps.

---

## Key Insights & Non-Obvious Details
At least 5 bullets:
- **[title]:** explanation

---

## Full Replication Checklist
Grouped phases with checkboxes:

**Phase 1: Setup & Prerequisites**
- [ ] action

**Phase N: name**
- [ ] action

---

## Resources & References
table: Resource | Type | Notes

---

### Quality standards:
- Every section complete, no placeholders
- Steps in exact tutorial order
- Code verbatim from transcript
- Replication Checklist must be AI-agent-executable alone
- Concrete names/numbers/examples from transcript
- Long is fine — depth is the goal

## Step 5: Derive Filename & Save

Run this to compute filename:

```bash
uv run python3 -c "
import re, sys, os

title = sys.argv[1]
slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:60]
base = f'tutorials/tutorial_{slug}'
filename = f'{base}.md'

if os.path.exists(filename):
    n = 2
    while os.path.exists(f'{base}_{n}.md'):
        n += 1
    filename = f'{base}_{n}.md'

print(filename)
" "VIDEO_TITLE"
```

Create tutorials/ directory if needed:
```bash
mkdir -p tutorials
```

Write the document to the computed filename using the Write tool.

## Step 6: Confirm & Cleanup

Print:
```
Tutorial saved: tutorials/tutorial_<slug>.md
Title:    [Video Title]
Channel:  [Channel Name]
Duration: [Duration]
Type:     [Tutorial type]

The guide covers [N] steps and is ready for reading or agent replication.
```

Clean up:
```bash
rm -f /tmp/dna-VIDEO_ID.en.vtt /tmp/dna-VIDEO_ID.en.srt /tmp/dna-transcript-VIDEO_ID.txt
```

## Important Notes

- **Only YouTube URLs** — no playlist positions, no other platforms.
- **Transcript is fatal** — stop if unavailable. No hallucinated guides.
- **This is not a summary** — complete instructional document. Depth first.
- **Dual audience** — human narrative + AI-executable checklist.
- **Local output only** — tutorials/ on disk. Nothing published to Notion.
- All dates use GST (GMT+4, Asia/Dubai).
