---
description: Show conversation statistics and usage patterns
argument-hint: [--project P] [--from DATE] [--to DATE] [--detailed]
---

Display usage statistics including total sessions, messages, projects, and activity patterns.

Run this command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/search_helper.py" stats $ARGUMENTS
```

Shows: Total sessions/messages, history size, top projects, activity by day, common topics.
