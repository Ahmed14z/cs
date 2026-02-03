---
description: Display a specific session's full conversation
argument-hint: <session-id> [--limit N] [--compact] [--export markdown|json]
---

View the full conversation from a specific session.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" show-session $ARGUMENTS
```

You can get session IDs from `/cs:sessions` command.
