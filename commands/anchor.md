---
description: Place a custom searchable marker at the current position
argument-hint: [label]
---

Place a unique searchable marker in the conversation that you can find later.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" anchor $ARGUMENTS
```

After output appears, use Ctrl+Shift+F and search `CS-ANCHOR-<YOUR-LABEL>` to navigate back.
