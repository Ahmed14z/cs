---
description: Search conversation history with text, regex, project, and date filters
argument-hint: <query> [--project P] [--regex] [--from DATE] [--to DATE] [--limit N]
---

Search through Claude Code conversation history to find past conversations, code snippets, and solutions.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" search $ARGUMENTS
```

Examples:
- `/cs:search "python async" --project manufacturing`
- `/cs:search "Error.*failed" --regex --from 2025-01-01`
- `/cs:search "SQL query" --limit 10`
