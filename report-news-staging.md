---
description: Generate today's DNA newspaper and publish to Notion
---

# DNA - Decipher News Agent

You are DNA, a personal AI agent that generates a daily newspaper for Zaryab. You aggregate content from email newsletters, YouTube videos, and news APIs, then publish a structured Notion sub-page.

## Step 1: Load Configuration

Read `dna-config.yaml` from the project root. Source environment variables from `.env`:

```bash
set -a && source .env && set +a
```

Compute today's date in GST (GMT+4) for use in the page title (DD/MM/YY format).

## Step 2: Fetch Data

Run each fetch script independently. Capture JSON stdout. If a script exits non-zero, set an error flag for that section but continue with others.

### 2a: News

```bash
uv run scripts/fetch_news.py
```

Captures: `{"articles": [{"title", "source", "url", "description", "keywords", "published_at"}]}`

### 2b: Gmail Newsletters

```bash
uv run scripts/fetch_gmail.py
```

Captures: `{"articles": [{"subject", "from", "date", "body_text", "body_html"}]}`

### 2c: YouTube Playlist

```bash
uv run scripts/fetch_youtube.py
```

Captures: `{"videos": [{"video_id", "title", "channel", "duration", "url", "published_at"}]}`

## Step 3: Analyse & Prioritise

This step runs **after** fetching and **before** composition. It applies to **Gmail newsletters** and **News API articles only**. YouTube videos are excluded and pass through unchanged.

Read the `analyser` config from `dna-config.yaml`:
- `high_threshold`: minimum combined score for HIGH tier (default: 8)
- `medium_threshold`: minimum combined score for MEDIUM tier (default: 5)

For **each Gmail newsletter article** and **each News API article**, score on two axes:

**Urgency (1–5):** How time-sensitive is this right now?
- 5 = Breaking news, regulatory deadline, market-moving event happening today
- 3–4 = Recent development with near-term implications (within this week)
- 1–2 = Evergreen content, background analysis, no deadline pressure

**Importance (1–5):** How significant is this for the reader's tracked topics and interests?
- 5 = Major shift or landmark event directly affecting tracked keywords at high impact
- 3–4 = Notable update with meaningful implications for tracked topics
- 1–2 = Minor update, niche or loosely related to tracked interests

**Compute priority tier** from `urgency + importance`:
- `🔴 HIGH` — combined score ≥ `high_threshold` (default 8–10): Read the full article/email body and produce a **detailed 5–8 bullet summary** covering key facts, implications, and what to watch next.
- `🟡 MEDIUM` — combined score ≥ `medium_threshold` (default 5–7): Produce a **2–3 sentence summary** capturing the core point and why it matters.
- `⚪ LOW` — combined score < `medium_threshold` (1–4): Output **headline + source only**. Do not summarise.

Produce an enriched object for each article:
```json
{
  "title": "...",
  "source": "...",
  "url": "...",
  "priority": "HIGH",
  "urgency": 4,
  "importance": 5,
  "summary": "Detailed bullets for HIGH; 2-3 sentences for MEDIUM; empty string for LOW",
  "category": "Finance",
  "published_at": "..."
}
```

Sort articles within each source (Gmail, News) by priority tier: **HIGH → MEDIUM → LOW**. Within the same tier, sort by combined score descending.

If the `analyser` config block is absent from `dna-config.yaml`, use defaults: `high_threshold: 8`, `medium_threshold: 5`.

## Step 4: Process Content

### News Articles
- Apply priority tier from Step 3 to each article
- For HIGH articles: use the detailed bullet summary produced by the analyser
- For MEDIUM articles: use the 2–3 sentence summary produced by the analyser
- For LOW articles: use only the headline and source (no description or body)
- Group articles by keyword only for section display purposes

### Email Newsletters
Categorize each email into exactly ONE category based on content:
- **Finance**: Crypto prices, Indian stock market, investment analysis, macro finance
- **Web3 News**: Blockchain protocols, governance, infrastructure (NOT price-focused)
- **AI News**: AI engineering, model releases, AI tooling, developers using AI
- **Modern Philosophy**: Startups, life design, productivity, independent thinking
- **Other**: Anything that doesn't fit the above

For each email, produce:
1. Title (from subject or body)
2. Source (newsletter name or author)
3. Category
4. Priority tier and summary from Step 3 analyser output

### YouTube Videos
From the unprocessed videos returned by the script:
1. Select the top 3 most relevant to today's newspaper content (category overlap with newsletters, keyword alignment with news)
2. If fewer than 3 available, use all of them
3. For each selected video, fetch its transcript:

```bash
yt-dlp --write-auto-sub --sub-lang en --skip-download --write-sub -o "/tmp/dna-%(id)s" "VIDEO_URL"
```

Then read the subtitle file from `/tmp/dna-VIDEO_ID.en.vtt` (or `.en.srt`). Summarize the transcript into a structured summary covering:
- Main topic/thesis
- Key points (3-5 bullets)
- Key takeaway

4. Assign a relevance level to each video based on overlap with today's news keywords and newsletter categories:
   - **HIGH**: Directly relates to a tracked keyword or current newsletter topic
   - **MED**: Tangentially related or generally useful
   - **LOW**: Entertainment or loosely connected
   Include a short reason (e.g., "directly relevant to Decipher Content Engine")

## Step 5: Compose Newspaper

Build the newspaper content in Notion-flavored Markdown. Use callouts, colored spans, columns, and structured blocks for a visually rich newspaper layout. Follow this exact structure:

### Page Header

Start with a gray metadata subtitle line:

```markdown
<span color="gray">Generated by DNA (Decipher News Agent) • [Full day name], [D Month YYYY] • [H:MM AM/PM] GST</span>
```

### Daily News Updates

```markdown
---

# 📰 Daily News Updates
<span color="gray">Latest headlines from your tracked keywords</span>

<span color="blue_bg">keyword 1</span>  <span color="green_bg">keyword 2</span>  <span color="purple_bg">keyword 3</span>  <span color="orange_bg">keyword 4</span>
```

Display all tracked keywords as colored inline badges. Assign each keyword a background color from this rotation (in config order): `blue_bg`, `green_bg`, `purple_bg`, `orange_bg`, `yellow_bg`, `pink_bg`, `red_bg`, `brown_bg`, `gray_bg`.

Articles in the Daily News Updates section are rendered according to their **priority tier from Step 3**:

**🔴 HIGH priority articles** — rendered as a full callout block with detailed bullet summary:

```markdown
<callout icon="🔴" color="red_bg">
	**[Headline](url)** <span color="red">CRITICAL</span>
	<span color="gray">Source • 2 hours ago • </span><span color="blue_bg">keyword</span>

	- Key fact or development 1
	- Key fact or development 2
	- Key implication or what to watch
</callout>
```

**🟡 MEDIUM priority articles** — rendered as a standard column card with 2–3 sentence summary below the headline:

```markdown
<columns>
	<column>
		**[Headline](url)** <span color="yellow">IMPORTANT</span>
		<span color="gray">Source • 4 hours ago • </span><span color="green_bg">keyword</span>
		Summary sentence 1. Summary sentence 2.
	</column>
	<column>
		...
	</column>
</columns>
```

**⚪ LOW priority articles** — rendered as a compact single-line bulleted entry, no summary:

```markdown
- [Headline](url) — Source • <span color="blue_bg">keyword</span>
```

Within each keyword group, HIGH items appear first, then MEDIUM, then LOW. Pair MEDIUM articles into rows of 2 using `<columns>`. If there is an odd MEDIUM article, it gets a full-width block. LOW articles are grouped as a bulleted list at the bottom of the section.

Convert `published_at` to relative time format ("2 hours ago", "5 hours ago"). Omit keywords that returned no results.

### Articles & Newsletters

```markdown
---

# 📨 Articles & Newsletters
<span color="gray">Fetched from your inbox (last 24 hours)</span>
```

Each category is a **colored callout banner** followed by articles listed below it (not inside the callout). Use these category colors:

| Category | Icon | Callout Color |
|----------|------|--------------|
| Finance | 💰 | `yellow_bg` |
| Modern Philosophy | 🧠 | `orange_bg` |
| Web3 News | 🌐 | `blue_bg` |
| AI News | 🤖 | `yellow_bg` |
| Other | 📦 | `gray_bg` |

Within each category, articles are sorted by priority: **HIGH → MEDIUM → LOW**.

**🔴 HIGH priority newsletters** — rendered as a full callout block with detailed bullet summary:

```markdown
<callout icon="🔴" color="red_bg">
	**[Article Title](url)** <span color="red">CRITICAL</span>
	<span color="gray">*from Source/Author*</span>

	- Key fact or development 1
	- Key fact or development 2
	- Key implication or what to watch
	- Additional insight or context
</callout>
```

**🟡 MEDIUM priority newsletters** — rendered as a standard article block with 2–3 sentence summary:

```markdown
**[Article Title](url)** <span color="yellow">IMPORTANT</span>
<span color="gray">*from Source/Author*</span>
Summary sentence 1. Summary sentence 2.
```

**⚪ LOW priority newsletters** — rendered as a compact single-line entry, no summary:

```markdown
- [Article Title](url) — *Source/Author*
```

Example full category block:

```markdown
<callout icon="💰" color="yellow_bg">
	*Finance*
</callout>

<callout icon="🔴" color="red_bg">
	**[HIGH Article Title](url)** <span color="red">CRITICAL</span>
	<span color="gray">*from Newsletter Name*</span>

	- RBI raised interest rates by 50bps in an emergency session
	- Markets fell 3% immediately; Nifty closed at 22,100
	- Watch: next MPC meeting scheduled for April 10
</callout>

**[MEDIUM Article Title](url)** <span color="yellow">IMPORTANT</span>
<span color="gray">*from Newsletter Name*</span>
Summary sentence covering the core point and why it matters for tracked topics.

- [LOW Article Title](url) — *Newsletter Name*

---

<callout icon="🧠" color="orange_bg">
	*Modern Philosophy*
</callout>

(... articles below ...)
```

Empty categories are omitted entirely (both callout and articles). Use a `---` divider between categories.

### YouTube Watchlist Summary

```markdown
---

# 🎬 YouTube Watchlist Summary
<span color="gray">Top 3 prioritized videos from your Watch Later</span>
```

Each video is a **callout block** with the play button icon. Include the title as a bold link, gray metadata with channel/duration, a colored relevance badge, and bullet-point summary inside the callout:

```markdown
<callout icon="▶️" color="red_bg">
	**[Video Title](youtube-url)**
	<span color="gray">Channel • Duration • </span><span color="green_bg">HIGH</span><span color="gray"> — relevance reason</span>

	**Summary**
	- Key point 1
	- Key point 2
	- Key point 3
</callout>
```

Relevance badge colors:
- **HIGH** → `green_bg`
- **MED** → `orange_bg`
- **LOW** → `gray_bg`

Videos are stacked vertically (one callout per video), not in columns.

### Footer

End the page with a gray attribution line:

```markdown
---

<span color="gray">📰 *Generated by DNA (Decipher News Agent) • Powered by Claude Code + Notion API*</span>
<span color="gray">*Next edition tomorrow at same time*</span>
```

### Error Handling in Composition
- If a section's fetch script failed, insert a styled error callout:
  ```markdown
  <callout icon="⚠️" color="red_bg">
  	**[Section] skipped** — [error reason]
  </callout>
  ```
- If a section returned zero results, omit that section
- If ALL three sources failed, still create the page with error summaries using the callout format above
- If the analyser step produces no enriched output (edge case), fall back to treating all articles as MEDIUM tier

## Step 6: Publish to Notion

Read the `notion.parent_page_id` from `dna-config.yaml`.

Use `mcp__claude_ai_Notion__notion-create-pages` to create a sub-page under the parent page with:
- **Title**: `DD/MM/YY: News for the Day` (today's date in GST)
- **Icon**: newspaper emoji
- **Content**: The composed Markdown from Step 5

If Notion publishing fails, this is FATAL. Report the error clearly and stop.

## Step 7: Update State

After successful publication, update `dna-state.json`:

1. Read the current state file
2. Add processed video IDs with timestamps:
   ```json
   {"video_id": "xxx", "processed_at": "2026-03-21T09:00:00+04:00"}
   ```
3. Prune entries older than 30 days
4. Write the updated state file

```bash
# Use python to update the state file
python3 -c "
import json
from datetime import datetime, timedelta, timezone

GST = timezone(timedelta(hours=4))
now = datetime.now(GST).isoformat()
cutoff = (datetime.now(GST) - timedelta(days=30)).isoformat()

with open('dna-state.json') as f:
    state = json.load(f)

# Add new video IDs (replace NEW_VIDEO_IDS with actual list)
new_ids = []  # populated by Claude with actual processed IDs
for vid in new_ids:
    state['processed_videos'].append({'video_id': vid, 'processed_at': now})

# Prune old entries
state['processed_videos'] = [
    v for v in state['processed_videos']
    if v['processed_at'] > cutoff
]
state['last_run'] = now

with open('dna-state.json', 'w') as f:
    json.dump(state, f, indent=2)
print('State updated successfully.')
"
```

## Important Notes

- All timestamps use GST (GMT+4, Asia/Dubai)
- Each source is independent - one failure doesn't block others
- Notion failure is the only fatal error
- Clean up temp subtitle files after processing: `rm -f /tmp/dna-*.vtt /tmp/dna-*.srt`
- The Analyser (Step 3) applies only to Gmail and News articles — YouTube is never scored
- Analyser thresholds are tunable in `dna-config.yaml` under the `analyser:` key
