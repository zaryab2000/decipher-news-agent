---
description: "Summarize a YouTube video and publish to Notion. Usage: /summarize <playlist-position-or-youtube-url>"
---

# /summarize — YouTube Video Summarizer

Summarize a YouTube video using the `summarize` CLI and publish the result as a Notion sub-page.

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

## Step 3: Run Summarize CLI

Using the video URL from Step 2, run the `summarize` CLI:

```bash
summarize "VIDEO_URL" --length long --youtube auto
```

Replace `VIDEO_URL` with the actual YouTube URL.

Use a timeout of 300000ms (5 minutes) since long videos take time to process.

Capture the full stdout output — this is the markdown summary.

### Error Handling

- If `summarize` is not found (command not found error), print:
  `"Error: 'summarize' CLI not found. Install with: npm i -g @steipete/summarize"`
  and stop.
- If `summarize` exits with a non-zero code, print the stderr output. Then retry once with an explicit model fallback:
  ```bash
  summarize "VIDEO_URL" --length long --youtube auto --model google/gemini-2.0-flash
  ```
  If the retry also fails, stop. Do NOT create a Notion page for a failed summarization.

## Step 4: Publish to Notion

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
> **Summarized on:** [DD/MM/YY]

---

[Full summary output from the summarize CLI, preserved exactly as-is.
Do not reformat, truncate, or modify the summary in any way.]
```

If Notion publishing fails, report the error clearly and stop.

## Step 5: Confirm

Print the Notion page URL and a confirmation message.

## Important Notes

- All dates use GST (GMT+4, Asia/Dubai)
- The `summarize` CLI auto-detects LLM provider from environment variables (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`)
- Notion failure is fatal — do not retry
- `summarize` failure is fatal — do not create a partial Notion page
