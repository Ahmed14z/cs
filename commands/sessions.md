---
description: List all conversation sessions with summaries and metadata
argument-hint: [--project P] [--limit N] [--sort date|size|messages]
---

List conversation sessions with their summaries, message counts, and dates.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" list-sessions $ARGUMENTS
```

Use the session IDs from the output with `claude --resume <session-id>` to jump to a specific conversation.
