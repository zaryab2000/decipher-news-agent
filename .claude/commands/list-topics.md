---
description: Show current DNA news topics/keywords
---

# List News Topics

Read `dna-config.yaml` from the project root. Extract the `news` section.

Display the current keywords as a numbered list:

```
Current news topics:
1. crypto prices
2. ethereum
...
```

Below the list, show the fetch settings:
- **Articles per keyword:** (value of `articles_per_keyword`)
- **Max total articles:** (value of `max_total_articles`)

Ignore any arguments (`$ARGUMENTS`). This command takes no input.
