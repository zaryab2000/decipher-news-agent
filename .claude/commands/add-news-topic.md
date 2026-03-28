---
description: "Add news topics/keywords to DNA config. Usage: /add-news-topic topic1, topic2, topic3"
---

# Add News Topics

Add one or more news keywords to `dna-config.yaml` so they are fetched in future `/report-news` runs.

## Input

Arguments: `$ARGUMENTS`

Parse the arguments as **comma-separated** topics. If there are no commas, treat the entire argument string as a single topic. Trim whitespace from each topic.

If no arguments were provided (empty string), ask the user what topics they want to add, then proceed.

If more than 3 topics are provided, warn the user ("Adding more than 3 topics at once increases fetch time") but proceed anyway.

## Steps

1. Read `dna-config.yaml` from the project root. Extract the current `news.keywords` list.

2. For each new topic:
   - Compare case-insensitively against existing keywords.
   - If it already exists, report: "**Skipped** '[topic]' — already exists"
   - If new, add it to the keywords list in the YAML file. Use the same quoted-string format as existing entries (e.g., `- "new topic"`).

3. Use the **Edit tool** to modify only the `news.keywords` section in `dna-config.yaml`. Do not rewrite the entire file.

4. Display the result:
   ```
   **Before:** [old keywords list]
   **Added:** [new keywords]
   **Skipped:** [duplicates, if any]
   **After:** [updated keywords list]
   ```

5. Ask the user: "Want me to fetch news for the new topics now?"
   - If yes: run `uv run scripts/fetch_news.py` and display the fetched articles.
   - If no: reply "New topics will be included in the next `/report-news` run."
