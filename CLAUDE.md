# DNA - Decipher News Agent

Personal AI agent that generates a daily newspaper by aggregating email newsletters, YouTube videos, and Google News RSS results, then publishes to Notion.

## Architecture

- `/report-news` slash command is the main entry point
- `/summarize` slash command summarizes individual YouTube videos
- Three Python scripts fetch data independently, output JSON to stdout
- Claude categorizes, summarizes, and composes the newspaper
- Notion MCP creates the sub-page
- State tracked in `dna-state.json` (gitignored) for YouTube video dedup and Gmail last-run timestamp

## Key Files

| File | Purpose |
|------|---------|
| `.claude/commands/report-news.md` | Daily newspaper slash command |
| `.claude/commands/summarize.md` | YouTube video summarizer slash command |
| `.claude/commands/add-news-topic.md` | Add news keywords to config |
| `.claude/commands/remove-news-topic.md` | Remove news keywords from config |
| `.claude/commands/list-topics.md` | Show current news keywords |
| `scripts/fetch_news.py` | Google News RSS fetcher (via `gnews` library) |
| `scripts/fetch_gmail.py` | Gmail newsletter fetcher (OAuth, state-aware) |
| `scripts/fetch_youtube.py` | YouTube playlist fetcher (OAuth, ID-based dedup) |
| `scripts/google_auth.py` | One-time OAuth setup |
| `dna-config.yaml` | All configuration (gitignored) |
| `dna-state.json` | Runtime state: processed videos, gmail last run (gitignored) |

## Running

```bash
# In Claude Code CLI:
/report-news              # Generate daily newspaper
/summarize 3              # Summarize 3rd video in DNA Summary playlist
/summarize <youtube-url>  # Summarize a specific video
/add-news-topic AI agents # Add a news keyword
/list-topics              # Show tracked keywords
```

## Config

- All config in `dna-config.yaml` (gitignored — contains personal Notion/YouTube IDs)
- Secrets in `.env` (gitignored)
- Timezone: Asia/Dubai (GMT+4)

## Data Flow

### /report-news
1. Fetches news (Google News RSS), emails (Gmail API), videos (YouTube API)
2. Claude categorizes emails, selects top 3 videos, downloads transcripts
3. Composes rich Notion page with columns, callouts, colored spans
4. Publishes via Notion MCP, updates `dna-state.json`

### /summarize
1. Resolves video from playlist position or URL
2. Extracts transcript via `youtube-transcript-api` (fallback: `yt-dlp`)
3. Claude produces structured summary (Overview, Key Points, Notable Quotes, Takeaways)
4. Publishes to Notion under YouTube Summaries page

## Error Handling

Each source can fail independently. Failed sections get a callout block in the Notion page. Only Notion failure is fatal.
