# DNA - Decipher News Agent

Personal AI agent that generates a daily newspaper by aggregating email newsletters, YouTube videos, and news API results, then publishes to Notion.

## Architecture

- `/report-news` slash command is the entry point
- Three Python scripts fetch data independently, output JSON to stdout
- Claude categorizes, summarizes, and composes the newspaper
- Notion MCP creates the sub-page

## Key Files

| File | Purpose |
|------|---------|
| `.claude/commands/report-news.md` | Slash command prompt (the brain) |
| `scripts/fetch_news.py` | NewsAPI/GNews fetcher |
| `scripts/fetch_gmail.py` | Gmail newsletter fetcher |
| `scripts/fetch_youtube.py` | YouTube playlist fetcher |
| `scripts/google_auth.py` | One-time OAuth setup |
| `dna-config.yaml` | All configuration |
| `dna-state.json` | YouTube processed video state |

## Running

```bash
# In Claude Code CLI:
/report-news
```

## Config

- All config in `dna-config.yaml`
- Secrets in `.env` (gitignored)
- Timezone: Asia/Dubai (GMT+4)

## Error Handling

Each source can fail independently. Failed sections get a callout block in the Notion page. Only Notion failure is fatal.
