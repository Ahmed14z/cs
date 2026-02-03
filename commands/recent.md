---
description: Show recent conversations across all projects
argument-hint: [--hours N] [--days N] [--project P]
---

Show recent conversation activity grouped by time.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" recent $ARGUMENTS
```

Examples:
- `/cs:recent` - Last 24 hours
- `/cs:recent --days 7` - Last week
- `/cs:recent --hours 48 --project manufacturing`
