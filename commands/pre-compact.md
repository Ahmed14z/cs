---
description: Show content from before the last compaction/summarization point
argument-hint: [--context N]
---

Recover context that was summarized during conversation compaction.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" pre-compact $ARGUMENTS
```

After output appears, use Ctrl+Shift+F and search `CS-ANCHOR-PRECOMPACT` to navigate here.
