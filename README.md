# DNA - Decipher News Agent

Personal AI agent that generates a daily newspaper from email newsletters, YouTube videos, and Google News RSS, published as a Notion sub-page. Also summarizes individual YouTube videos on demand.

## Setup

### 1. Install Dependencies

```bash
uv venv && uv sync
brew install yt-dlp
```

### 2. Google Cloud Setup

1. Create a Google Cloud project
2. Enable **Gmail API** and **YouTube Data API v3**
3. Create **OAuth 2.0 Desktop app** credentials
4. Copy client ID and secret to `.env`:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   ```
5. Run the auth script and complete browser consent:
   ```bash
   uv run scripts/google_auth.py
   ```
6. Copy the printed refresh token to `.env`:
   ```
   GOOGLE_REFRESH_TOKEN=your_refresh_token
   ```

### 3. Gmail Setup

Create a Gmail filter that auto-labels incoming newsletters with `dna-queue`.

### 4. YouTube Setup

1. Create a "DNA Queue" playlist on YouTube (for daily newspaper videos)
2. Create a "DNA Summary" playlist on YouTube (for on-demand summarization)
3. Copy both playlist IDs to `dna-config.yaml`

### 5. Notion Setup

1. Create a parent page in Notion for the daily newspaper
2. Create a separate page for YouTube summaries
3. Copy both page IDs to `dna-config.yaml`
4. Share both pages with the Notion MCP integration

### 6. Config

Copy and fill `dna-config.yaml` with your IDs:

```yaml
timezone: "Asia/Dubai"

gmail:
  label: "dna-queue"
  lookback_hours: 24
  max_full_articles: 15

youtube:
  playlist_id: "YOUR_QUEUE_PLAYLIST_ID"
  dna_summary_playlist_id: "YOUR_SUMMARY_PLAYLIST_ID"
  max_videos: 3
  state_file: "dna-state.json"

news:
  source: "google_news_rss"
  keywords:
    - "ethereum"
    - "artificial intelligence"
  articles_per_keyword: 3
  max_total_articles: 15

notion:
  parent_page_id: "YOUR_NEWSPAPER_PAGE_ID"
  youtube_summaries_page_id: "YOUR_SUMMARIES_PAGE_ID"
  sub_page_title_format: "DD/MM/YY: News for the Day"
  icon: "📰"

categories:
  - Finance
  - Web3 News
  - AI News
  - Modern Philosophy
  - Other
```

## Usage

In Claude Code CLI:

```bash
/report-news                                           # Generate daily newspaper
/summarize 3                                           # Summarize 3rd video in DNA Summary playlist
/summarize https://www.youtube.com/watch?v=VIDEO_ID    # Summarize a specific video
/add-news-topic topic1, topic2                         # Add news keywords
/remove-news-topic topic1                              # Remove a news keyword
/list-topics                                           # Show current keywords
```

## Testing Individual Scripts

```bash
uv run scripts/fetch_news.py        # Google News RSS
uv run scripts/fetch_gmail.py       # Gmail newsletters
uv run scripts/fetch_youtube.py     # YouTube playlist
```

Each script outputs JSON to stdout. Errors go to stderr with non-zero exit.

## Tech Stack

- Python 3.13, uv, hatchling
- `gnews` for Google News RSS (free, no API key)
- `youtube-transcript-api` for transcript extraction (free, no API key)
- `yt-dlp` for transcript fallback (brew installed)
- Google OAuth 2.0 for Gmail and YouTube APIs
- Notion via MCP (Claude Code integration)
