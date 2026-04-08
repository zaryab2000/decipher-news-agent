---
description: "Summarize a YouTube video and publish to Notion. Usage: /summarize <playlist-position-or-youtube-url>"
---

# /summarize — YouTube Video Summarizer

Summarize a YouTube video and publish the result as a Notion sub-page. Transcript extraction uses `youtube-transcript-api` (free, no API key). Summarization is done by Claude directly (no external LLM).

## Step 1: Parse Input & Load Config

The input is: `$ARGUMENTS`

If the input is empty, print this usage message and stop:
```
Usage: /summarize <playlist-position-or-youtube-url>

Examples:
  /summarize 4                                          — 4th video in DNA Summary playlist
  /summarize https://www.youtube.com/watch?v=VIDEO_ID   — direct URL
```

Determine the input format:
- If the input is a pure integer (matches `^\d+$`): treat as **playlist index** (1-indexed).
- If the input contains `youtube.com` or `youtu.be`: treat as **direct YouTube URL**.
- Otherwise: print `"Invalid argument. Use a playlist position number or a YouTube URL."` and stop.

Source environment variables:
```bash
set -a && source .env && set +a
```

Read `dna-config.yaml` from the project root.

## Step 2: Resolve Video Metadata

### Path A: Playlist Index

Read `youtube.dna_summary_playlist_id` from config. If missing or set to `[USER TO PROVIDE]`, print:
`"Error: youtube.dna_summary_playlist_id not configured in dna-config.yaml. Create a 'DNA Summary' playlist on YouTube and add its ID to the config."`
and stop.

Fetch the playlist items and extract the video at the requested position:

```bash
uv run python3 -c "
import json, os, sys, re
import requests

# Args: playlist_id, 1-indexed position
playlist_id = sys.argv[1]
position = int(sys.argv[2])

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
headers = {'Authorization': f'Bearer {token}'}

# Fetch playlist items (paginate until we have enough)
items = []
page_token = None
while len(items) < position:
    params = {'part': 'snippet', 'playlistId': playlist_id, 'maxResults': 50}
    if page_token:
        params['pageToken'] = page_token
    r = requests.get('https://www.googleapis.com/youtube/v3/playlistItems',
                     params=params, headers=headers, timeout=15)
    if r.status_code != 200:
        print(f'Playlist fetch failed: {r.status_code} {r.text}', file=sys.stderr)
        sys.exit(1)
    data = r.json()
    items.extend(data.get('items', []))
    page_token = data.get('nextPageToken')
    if not page_token:
        break

if len(items) == 0:
    print('Error: The DNA Summary playlist is empty.', file=sys.stderr)
    sys.exit(1)
if position > len(items):
    print(f'Error: Position {position} is out of range. The playlist has {len(items)} videos.', file=sys.stderr)
    sys.exit(1)

item = items[position - 1]
video_id = item['snippet']['resourceId']['videoId']
title = item['snippet']['title']
channel = item['snippet'].get('videoOwnerChannelTitle', 'Unknown')

# Fetch duration
dr = requests.get('https://www.googleapis.com/youtube/v3/videos',
                   params={'part': 'contentDetails', 'id': video_id},
                   headers=headers, timeout=15)
duration = ''
if dr.status_code == 200:
    vitems = dr.json().get('items', [])
    if vitems:
        iso = vitems[0]['contentDetails']['duration']
        m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso)
        if m:
            h, mn, s = int(m.group(1) or 0), int(m.group(2) or 0), int(m.group(3) or 0)
            duration = f'{h}:{mn:02d}:{s:02d}' if h else f'{mn}:{s:02d}'

json.dump({
    'video_id': video_id, 'title': title, 'channel': channel,
    'duration': duration, 'url': f'https://www.youtube.com/watch?v={video_id}'
}, sys.stdout)
" "PLAYLIST_ID" "POSITION"
```

Replace `PLAYLIST_ID` with the value from config and `POSITION` with the user's input.

### Path B: Direct YouTube URL

Extract the video ID from the URL and fetch metadata:

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

Replace `YOUTUBE_URL` with the user's input URL.

## Step 3: Extract Transcript

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
```
Stop execution. Do NOT create a Notion page without a transcript.

### Long videos (3+ hours)

If the transcript output exceeds 30,000 characters, write it to `/tmp/dna-transcript-VIDEO_ID.txt` first, then read it with the Read tool.

## Step 4: Summarize Transcript

You now have the full transcript from Step 3. Produce a structured summary in markdown following this exact structure:

### Overview
A single paragraph (3-5 sentences) capturing the video's main thesis, who it's for, and why it matters.

### Key Points
- **[Point title]**: Explanation in 1-2 sentences.

Include 5-8 key points, ordered by importance, not chronologically.

### Notable Quotes
> "Exact quote from the transcript"
> — Speaker (if identifiable) or "Host"

Include 2-4 of the most impactful or memorable quotes. Only use EXACT words from the transcript — do not paraphrase. If unsure of exact wording, omit the quote.

### Takeaways
1. Actionable takeaway

Include 3-5 concrete, actionable takeaways the viewer should remember.

### Quality Guidelines
- Do NOT start with "This video explores..." or "In this video..." — lead with the insight itself
- Be specific: use names, numbers, and concrete examples from the transcript
- If the video has a clear argument or thesis, state it directly in the overview
- Key points should be substantive insights, not vague topic headers
- Takeaways should be things the viewer can act on, not restatements of what was discussed

## Step 5: Publish to Notion

Compute today's date in GST (GMT+4) in DD/MM/YY format.

Read `notion.youtube_summaries_page_id` from `dna-config.yaml`.

Use `mcp__claude_ai_Notion__notion-create-pages` to create a sub-page:

- **Parent:** `{ "type": "page_id", "page_id": "<youtube_summaries_page_id>" }`
- **Title:** The video title from Step 2
- **Icon:** 🎥
- **Content:**

```markdown
> **Channel:** [Channel Name]
> **Duration:** [Duration]
> **Link:** [YouTube URL]
> **Summarized on:** [DD/MM/YY in GST]

---

## Overview
[Overview paragraph from Step 4]

## Key Points
[Key points from Step 4]

## Notable Quotes
[Quotes from Step 4]

## Takeaways
[Takeaways from Step 4]
```

If Notion publishing fails, report the error clearly and stop.

## Step 6: Confirm & Cleanup

Print the Notion page URL and a confirmation message.

Clean up any temp files:
```bash
rm -f /tmp/dna-VIDEO_ID.en.vtt /tmp/dna-VIDEO_ID.en.srt /tmp/dna-transcript-VIDEO_ID.txt
```

## Important Notes

- All dates use GST (GMT+4, Asia/Dubai)
- Transcript extraction failure is fatal — do not create a Notion page without a transcript
- Claude (the agent running this command) performs the summarization directly — no external LLM API needed
- For videos without captions, neither extraction method will work — inform the user and stop
- Notion failure is fatal — do not retry
