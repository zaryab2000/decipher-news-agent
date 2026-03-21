# DNA - Decipher News Agent

Personal AI agent that generates a daily newspaper from email newsletters, YouTube videos, and news APIs, published as a Notion sub-page.

## Setup

### 1. Install Dependencies

```bash
uv venv && uv pip install -e .
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

Create a Gmail filter that auto-labels incoming newsletters with `DNA/Newsletters`.

### 4. YouTube Setup

1. Create a "DNA Queue" playlist on YouTube
2. Copy the playlist ID to `dna-config.yaml` under `youtube.playlist_id`

### 5. News API Setup

1. Create a [NewsAPI.org](https://newsapi.org) account
2. Copy API key to `.env` as `NEWS_API_KEY`
3. (Optional) Create a [GNews.io](https://gnews.io) account for fallback, set `GNEWS_API_KEY`

### 6. Notion Setup

1. Create a "Zaryab's Newspaper" page in Notion
2. Copy the page ID to `dna-config.yaml` under `notion.parent_page_id`
3. Share the page with the Notion MCP integration

## Usage

In Claude Code CLI:

```bash
/report-news
```

## Testing Individual Scripts

```bash
uv run scripts/fetch_news.py        # News API
uv run scripts/fetch_gmail.py       # Gmail newsletters
uv run scripts/fetch_youtube.py     # YouTube playlist
```

Each script outputs JSON to stdout. Errors go to stderr with non-zero exit.
