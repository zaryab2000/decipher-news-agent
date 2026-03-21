# DNA — Decipher News Agent: v1 Product Spec

> **Version:** 1.0-draft
> **Author:** Zaryab + Claude
> **Last Updated:** 2026-03-21
> **Status:** Pending final sign-off

fresh new github for this project: https://github.com/zaryab2000/decipher-news-agent
---

## 1. Product Vision

DNA is a personal AI agent that generates a daily personalized newspaper for Zaryab. It aggregates content from three sources — email newsletters, a curated YouTube playlist, and keyword-based news APIs — processes and categorizes it, then publishes a structured Notion sub-page under a persistent parent page.

**v1 is not autonomous.** It runs on-demand via Claude Code CLI, with an experimental Telegram bridge as a secondary trigger.

---

## 2. Architecture Overview

```
Trigger (CLI or Telegram)
        │
        ▼
   DNA Agent (Claude Code)
        │
        ├──► Gmail API ──► Newsletter emails (label-filtered)
        │         │
        │         ▼
        │    Categorize + Summarize
        │
        ├──► YouTube Data API v3 ──► Custom playlist ("DNA Queue")
        │         │
        │         ▼
        │    Prioritize → summarizer.sh → Summaries
        │
        ├──► News API ──► Keyword search (5 keywords)
        │         │
        │         ▼
        │    Filter + Format
        │
        └──► Notion API ──► Create sub-page under "Zaryab's Newspaper"
```

---

## 3. Trigger Mechanism

### 3.1 Primary: Claude Code CLI

DNA is invoked via a custom slash command:

```bash
/report-news
```

This triggers the full pipeline: fetch → process → publish.

The command lives in the project's `.claude/commands/` directory as `report-news.md`. It contains the full agent prompt — data sources, processing rules, output format, and Notion target.

### 3.2 Experimental: Telegram Bot

Uses the official Telegram plugin from `anthropics/claude-plugins-official`.

```bash
claude --channels plugin:telegram@claude-plugins-official
```

The user sends `/report-news` as a DM to the Telegram bot, which forwards the command to the running Claude Code session.

**Known limitation (as of 2026-03-21):** The `--channels` feature has an open bug where inbound Telegram messages don't trigger Claude responses, even though the MCP tools (reply, react, edit) work. This is documented in `anthropics/claude-code#36503`. The Telegram trigger is opt-in and should be treated as experimental until the bug is resolved upstream.

**Fallback behavior:** If Telegram trigger fails, the user falls back to CLI. The agent logic is identical regardless of trigger source.

---

## 4. Data Sources

### 4.1 Email Newsletters (Gmail)

**Objective:** Fetch, categorize, and summarize newsletter/article emails received in the last 24 hours.

#### Filtering Strategy

- **Method:** Gmail label-based filtering.
- **Prerequisite:** The user creates a Gmail filter rule that auto-labels incoming newsletters with the label `DNA/Newsletters`. This is managed entirely in Gmail, outside the agent.
- **Query:** DNA queries Gmail for messages matching:
  ```
  label:DNA/Newsletters after:YYYY/MM/DD before:YYYY/MM/DD is:unread
  ```
- **Time window:** From 9:00 AM GST (GMT+4) on the previous day to the current trigger time. All timestamps are normalized to **Gulf Standard Time (GMT+4)**.

#### Categorization

Each email is classified into exactly **one** primary category. If an article spans multiple categories, DNA assigns the single best-fit category based on the article's primary focus.

| Category              | Description                                                            | Examples                                                |
| --------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------- |
| **Finance**           | Crypto prices, Indian stock market, investment analysis, macro finance | Finshots, CoinDesk market updates, ET Markets           |
| **Modern Philosophy** | Startups, life design, productivity, independent thinking              | Dan Koe, Cal Newport, Paul Graham essays                |
| **Web3 News**         | Blockchain protocols, governance, infrastructure — NOT price-focused   | Bankless protocol deep-dives, Ethereum core dev updates |
| **AI News**           | AI engineering, model releases, AI tooling, developers using AI        | Pragmatic Engineer AI coverage, The Batch, Latent Space |
| **Other**             | Anything that doesn't fit the above four categories                    | Design newsletters, health content, general tech        |

**"Other" is a catch-all.** DNA should not force-fit content into the four primary categories. If uncertain, default to "Other."

#### Output per Article

For each newsletter/article email, DNA produces:

1. **Title** — the article's title (extracted from email subject or body)
2. **Source** — newsletter name or author (e.g., "Finshots", "Dan Koe")
3. **Category** — one of the five categories above
4. **Summary** — 1–2 sentences. Enough to decide whether to read the full article. No filler, no "this article explores..." phrasing.

#### Edge Cases

- **Zero newsletters in window:** The Articles section is omitted from the newspaper with a note: "No newsletters received in the last 24 hours."
- **Email auth failure:** DNA logs the error, skips the Articles section, and continues with other sections. The published newspaper includes a note: "⚠️ Email fetch failed — Articles section skipped."

---

### 4.2 YouTube Watchlist Summary

**Objective:** Summarize the top 3 most relevant videos from a curated YouTube playlist.

#### Playlist Setup

- **Playlist type:** A custom, user-created YouTube playlist (not Watch Later — Watch Later is API-inaccessible).
- **Playlist name:** "DNA Queue" (or user's preferred name).
- **Playlist ID:** `[PENDING — user to provide]`
- **API:** YouTube Data API v3 with OAuth 2.0 (read-only scope: `youtube.readonly`).

#### Processing Logic

1. **Fetch playlist items** via `playlistItems.list`.
2. **Determine unprocessed videos** using a local state file (`dna-state.json`) that tracks previously processed video IDs. Videos already in the state file are skipped.
3. **If fewer than 3 unprocessed videos exist:** Include all available. Do not go beyond the playlist contents. If zero unprocessed videos exist, omit the YouTube section with a note: "No new videos in DNA Queue."
4. **Prioritize:** From unprocessed videos, select the top 3 based on relevance to the rest of that day's newspaper content (category overlap with newsletter topics, keyword alignment with news section).
5. **Summarize:** Run each selected video through `summarizer.sh` to generate a structured summary.
6. **Update state:** Add processed video IDs to `dna-state.json` after successful summarization.

#### summarizer.sh

- **Status:** Exists — details pending from user.
- **Expected interface:** `[PENDING — user to share script details, input/output format, and dependencies]`
- **Assumed behavior (to be confirmed):** Takes a YouTube video URL or ID as input, extracts the transcript (likely via `yt-dlp`), and produces a structured summary via LLM.

#### Output per Video

1. **Title** — video title
2. **Channel** — channel name
3. **Duration** — video length
4. **Summary** — structured summary as produced by `summarizer.sh`
5. **Link** — direct YouTube URL

#### Edge Cases

- **Playlist empty or all videos already processed:** YouTube section is omitted with a note.
- **`summarizer.sh` fails for a specific video:** Skip that video, log the error, attempt the next. If all 3 fail, omit the section with an error note.
- **YouTube API auth failure:** Skip entire YouTube section with error note. Continue with other sections.

---

### 4.3 Daily News Updates

**Objective:** Fetch current news for predefined keywords using a public news API.

#### API Selection

- **Primary:** [NewsAPI.org](https://newsapi.org) — `/v2/everything` endpoint.
- **Free tier limits:** 100 requests/day, articles up to 1 month old.
- **Fallback:** GNews API (`gnews.io`) if NewsAPI quota is exhausted or unreliable.
- **API key:** Stored in project `.env` file as `NEWS_API_KEY`.

#### Keywords

```yaml
keywords:
  - "crypto prices"
  - "ethereum"
  - "indian stock market"
  - "blockchain"
  - "artificial intelligence"
```

Keywords are stored in the project config file (see Section 7) and can be modified without changing agent code.

#### Processing Logic

1. For each keyword, fetch top 3 articles from the last 24 hours, sorted by relevance.
2. Deduplicate across keywords (same article URL appearing for multiple keywords → keep once, tag with all matching keywords).
3. Filter out obviously low-quality sources (listicles, SEO farms). DNA uses a source quality heuristic: prefer outlets with established editorial teams (Reuters, CoinDesk, TechCrunch, etc.) over aggregators.

#### Output per News Item

1. **Headline** — article title
2. **Source** — publication name
3. **Keywords** — which of the 5 keywords matched
4. **Snippet** — 1–2 sentence summary (use API-provided description if adequate, otherwise generate)
5. **Link** — article URL

#### Target: 3–5 articles per keyword, 10–15 total after deduplication.

#### Edge Cases

- **API returns zero results for a keyword:** Note "No recent news found for [keyword]" inline.
- **API rate limit hit:** Use fallback API. If both fail, skip News section with error note.
- **All keywords return nothing:** Omit News section with a note.

---

## 5. Output: Notion Newspaper

### 5.1 Page Structure

- **Parent page:** "Zaryab's Newspaper" — `[PENDING — user to provide page ID]`
- **Sub-page title format:** `DD/MM/YY: News for the Day`
- **Sub-page icon:** 📰

### 5.2 Section Order

The newspaper follows a fixed section order:

```
1. Daily News Updates
2. Articles & Newsletters
3. YouTube Watchlist Summary
```

### 5.3 Notion Content Format

DNA creates the sub-page using the Notion API. Below is the content structure using Notion-flavored Markdown:

```markdown
# 📰 Daily News Updates

## Crypto Prices
- **[Headline]** — *Source*
  Summary snippet. [Read →](link)

## Ethereum
- **[Headline]** — *Source*
  Summary snippet. [Read →](link)

(... grouped by keyword)

---

# 📬 Articles & Newsletters

## Finance
- **[Article Title]** — *Source/Author*
  Summary.

## Web3 News
- **[Article Title]** — *Source/Author*
  Summary.

## AI News
(...)

## Modern Philosophy
(...)

## Other
(...)

(Empty categories are omitted entirely — no empty headers.)

---

# 🎥 YouTube Watchlist

## 1. [Video Title]
**Channel:** Channel Name · **Duration:** 12:34
Summary from summarizer.sh
[Watch →](youtube-link)

## 2. [Video Title]
(...)

## 3. [Video Title]
(...)
```

### 5.4 Formatting Rules

- Articles within each category are listed chronologically (newest first).
- News items are grouped by keyword, with each keyword as an H2 under the News section.
- YouTube videos are numbered by priority rank (1 = most relevant).
- Empty sections are omitted entirely — no placeholder headers for sections with zero content.
- If a section was skipped due to an error, a callout block is inserted: `⚠️ [Section] skipped — [reason]`.
- Dividers (`---`) separate the three main sections.

---

## 6. Timezone

All time calculations use **Gulf Standard Time (GMT+4)**. This applies to:

- The 24-hour lookback window for Gmail queries
- The "last 24 hours" logic for YouTube playlist processing
- The date in the sub-page title (`DD/MM/YY`)
- News API date range parameters

---

## 7. Configuration

All configurable values live in a single YAML file: `dna-config.yaml` in the project root.

```yaml
# dna-config.yaml

timezone: "Asia/Dubai"  # GMT+4

# Gmail
gmail:
  label: "DNA/Newsletters"
  lookback_hours: 24

# YouTube
youtube:
  playlist_id: "[PENDING]"
  max_videos: 3
  state_file: "dna-state.json"

# News
news:
  primary_api: "newsapi"        # newsapi | gnews
  api_key_env: "NEWS_API_KEY"   # env var name, not the key itself
  keywords:
    - "crypto prices"
    - "ethereum"
    - "indian stock market"
    - "blockchain"
    - "artificial intelligence"
  articles_per_keyword: 3
  max_total_articles: 15

# Notion
notion:
  parent_page_id: "[PENDING]"
  sub_page_title_format: "DD/MM/YY: News for the Day"
  icon: "📰"

# Article categories (ordered by display priority)
categories:
  - Finance
  - Web3 News
  - AI News
  - Modern Philosophy
  - Other
```

---

## 8. State Management

### 8.1 `dna-state.json`

Tracks processed YouTube video IDs to avoid re-summarizing.

```json
{
  "processed_videos": [
    { "video_id": "abc123", "processed_at": "2026-03-20T09:15:00+04:00" },
    { "video_id": "def456", "processed_at": "2026-03-19T09:22:00+04:00" }
  ],
  "last_run": "2026-03-20T09:15:00+04:00"
}
```

- Entries older than 30 days are pruned on each run to prevent unbounded growth.
- State file is committed to the project repo (it's not sensitive data).

### 8.2 No Email State Needed

Gmail filtering is time-window-based (`after:` / `before:` parameters), so no local state tracking is needed for emails. The `is:unread` flag is optional but recommended to avoid re-processing.

---

## 9. Error Handling

DNA follows a **partial-success** strategy. If one data source fails, the other sections still publish. The newspaper always gets created — even if it only has one section.

| Failure                                | Behavior                                                                        |
| -------------------------------------- | ------------------------------------------------------------------------------- |
| Gmail auth fails                       | Skip Articles section. Insert error callout. Continue.                          |
| Gmail returns 0 newsletters            | Omit Articles section. Insert note. Continue.                                   |
| YouTube API auth fails                 | Skip YouTube section. Insert error callout. Continue.                           |
| YouTube playlist empty / all processed | Omit YouTube section. Insert note. Continue.                                    |
| `summarizer.sh` fails for 1 video      | Skip that video. Try next. Log error.                                           |
| `summarizer.sh` fails for all videos   | Omit YouTube section. Insert error callout. Continue.                           |
| News API rate-limited                  | Try fallback API. If both fail, skip News section. Insert error callout.        |
| News API returns 0 for a keyword       | Insert "No news found for [keyword]" inline. Continue.                          |
| Notion API fails                       | **Fatal.** Log error. Notify user via CLI/Telegram. Do not retry automatically. |
| All three sources fail                 | Create a minimal Notion page with a single error summary. Don't silently fail.  |

---

## 10. Authentication & Secrets

| Service          | Auth Method                              | Storage                          |
| ---------------- | ---------------------------------------- | -------------------------------- |
| Gmail            | OAuth 2.0 (scopes: `gmail.readonly`)     | Token file in project `.claude/` |
| YouTube          | OAuth 2.0 (scopes: `youtube.readonly`)   | Token file in project `.claude/` |
| NewsAPI          | API key                                  | `.env` as `NEWS_API_KEY`         |
| GNews (fallback) | API key                                  | `.env` as `GNEWS_API_KEY`        |
| Notion           | Integration token (internal integration) | `.env` as `NOTION_API_KEY`       |

**Security rules:**
- `.env` is in `.gitignore`. Never committed.
- Token files in `.claude/` are in `.gitignore`.
- No secrets appear in logs, Notion output, or state files.

---

## 11. Project File Structure

```
dna/
├── .claude/
│   ├── commands/
│   │   └── report-news.md          # Slash command prompt
│   └── channels/
│       └── telegram/               # Telegram bot config (experimental)
├── CLAUDE.md                        # Project-level Claude Code context
├── dna-config.yaml                  # All configurable values
├── dna-state.json                   # YouTube processed video state
├── .env                             # API keys (gitignored)
├── .gitignore
├── summarizer.sh                    # YouTube video summarizer [PENDING details]
└── README.md                        # Setup instructions
```

---

## 12. Pending Items (Blockers Before Build)

| #   | Item                                                                   | Owner  | Status    |
| --- | ---------------------------------------------------------------------- | ------ | --------- |
| 1   | Share `summarizer.sh` details (interface, dependencies, output format) | Zaryab | ⏳ Pending |
| 2   | Provide Notion parent page ID for "Zaryab's Newspaper"                 | Zaryab | ⏳ Pending |
| 3   | Provide YouTube "DNA Queue" playlist ID                                | Zaryab | ⏳ Pending |
| 4   | Set up Gmail filter → auto-label newsletters as `DNA/Newsletters`      | Zaryab | ⏳ Pending |
| 5   | Create NewsAPI.org account + get API key                               | Zaryab | ⏳ Pending |
| 6   | Set up YouTube OAuth 2.0 credentials (Google Cloud Console)            | Zaryab | ⏳ Pending |
| 7   | Set up Gmail OAuth 2.0 credentials (Google Cloud Console)              | Zaryab | ⏳ Pending |
| 8   | Create Notion internal integration + share parent page with it         | Zaryab | ⏳ Pending |

---

## 13. Future (Out of Scope for v1)

These are explicitly **not** in v1 but noted for future consideration:

- **Autonomous scheduling** — cron/scheduler to trigger DNA at 9 AM daily without manual invocation.
- **Telegram as primary trigger** — once the channels bug is resolved upstream.
- **Read-it-later integration** — Pocket/Instapaper as an additional article source.
- **Notion database instead of sub-pages** — structured database with filterable properties (category, source, date) instead of flat sub-pages.
- **Feedback loop** — mark articles as "read" or "useful" in Notion; DNA learns preferences over time.
- **Multi-user support** — DNA generates newspapers for other team members with different keyword/category configs.
- **RSS feeds** — as an additional or alternative source to Gmail for newsletters.
