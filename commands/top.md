---
description: Jump to conversation start - outputs first messages with a searchable anchor
argument-hint: [--limit N]
---

Output the beginning of the current conversation with a unique searchable anchor.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" top $ARGUMENTS
```

After output appears, use Ctrl+Shift+F in your terminal and search for `CS-ANCHOR-TOP` to navigate back to this point.
