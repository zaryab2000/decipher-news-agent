---
description: "Remove news topics/keywords from DNA config. Usage: /remove-news-topic topic1, topic2"
---

# Remove News Topics

Remove one or more news keywords from `dna-config.yaml`.

## Input

Arguments: `$ARGUMENTS`

Parse the arguments as **comma-separated** topics. If there are no commas, treat the entire argument string as a single topic. Trim whitespace from each topic.

If no arguments were provided (empty string):
1. Read `dna-config.yaml` and display the current keywords as a numbered list.
2. Ask the user which topics to remove (by name or number).
3. Proceed with their selection.

## Steps

1. Read `dna-config.yaml` from the project root. Extract the current `news.keywords` list.

2. For each topic to remove:
   - Match **case-insensitively** against existing keywords.
   - If found, remove it.
   - If not found, report: "**Skipped** '[topic]' — not found in keywords"

3. **Safety check:** If removal would leave the keywords list empty, warn the user and ask for confirmation before proceeding. An empty keywords list means `/report-news` will have no news section.

4. Use the **Edit tool** to modify only the `news.keywords` section in `dna-config.yaml`. Do not rewrite the entire file.

5. Display the updated keyword list. Note: "Changes take effect on the next `/report-news` run."
