# CS - Conversation Search Plugin for Claude Code

Navigate and search through your Claude Code conversation history with teleportation anchors and full-text search.

## Features

- **Teleportation Anchors** - Jump to conversation start, before compaction, or custom markers
- **Keyword Search** - Find mentions of specific terms with highlighted context
- **Full-text Search** - Search across all conversations with regex support
- **Session Browsing** - List and view conversation sessions with summaries
- **Usage Statistics** - Analyze your coding patterns and activity
- **Export Support** - Export conversations to markdown or JSON

## Installation

### From Plugin Directory

```bash
claude --plugin-dir /path/to/conversation-search-plugin
```

### From Marketplace (coming soon)

```bash
claude /install cs
```

## Commands

### Teleportation Commands

#### `/cs:top`
Jump to the beginning of the current conversation.

```bash
/cs:top              # Show first 5 messages (default)
/cs:top --limit 10   # Show first 10 messages
```

After running, use **Ctrl+Shift+F** in your terminal and search for `CS-ANCHOR-TOP` to navigate to this point.

#### `/cs:pre-compact`
Jump to content before the last conversation compaction (summary).

```bash
/cs:pre-compact           # Show context before compaction
/cs:pre-compact --limit 5 # Limit messages shown
```

Search for `CS-ANCHOR-PRE-COMPACT` to navigate here.

#### `/cs:find`
Quick keyword search in the current conversation.

```bash
/cs:find "database"       # Find mentions of "database"
/cs:find "error" --limit 5
```

Search for `CS-ANCHOR-FIND` to navigate to results.

#### `/cs:anchor`
Place a custom searchable anchor with optional note.

```bash
/cs:anchor                    # Create anchor with auto-generated name
/cs:anchor --name "bugfix"    # Create named anchor
/cs:anchor --name "todo" --note "Fix this later"
```

Search for `CS-ANCHOR-bugfix` or your custom name to navigate back.

### Search & Browse Commands

#### `/cs:search`
Search through all conversation history.

```bash
/cs:search "python async"                    # Basic search
/cs:search "API" --project manufacturing     # Filter by project
/cs:search "Error.*timeout" --regex          # Regex search
/cs:search "bug" --from 2025-01-01           # Date filter
/cs:search "implement" --context 5           # More context lines
```

**Options:**
- `--project, -p`: Filter by project path
- `--regex, -r`: Treat query as regex
- `--from/--to`: Date range (YYYY-MM-DD)
- `--context, -c`: Surrounding messages (default: 2)
- `--limit, -l`: Max results (default: 20)
- `--type, -t`: Filter by type (user, assistant, summary)

#### `/cs:sessions`
List all conversation sessions.

```bash
/cs:sessions                         # List all sessions
/cs:sessions --project myproject     # Filter by project
/cs:sessions --sort messages         # Sort by message count
/cs:sessions --limit 10
```

Use session IDs with `claude --resume <session-id>` to continue a conversation.

#### `/cs:show`
Display a specific session's full conversation.

```bash
/cs:show abc123                      # Show session (partial ID match)
/cs:show abc123 --compact            # Truncate long messages
/cs:show abc123 --export markdown    # Export to markdown
/cs:show abc123 --export json        # Export to JSON
```

#### `/cs:recent`
Show recent conversation activity.

```bash
/cs:recent                           # Last 24 hours
/cs:recent --days 7                  # Last week
/cs:recent --hours 48 --project mfg  # 48 hours, specific project
```

#### `/cs:stats`
Show conversation statistics and usage patterns.

```bash
/cs:stats                            # Overall statistics
/cs:stats --project manufacturing    # Project-specific
/cs:stats --detailed                 # Full breakdown
```

## How Teleportation Works

Since terminal TUIs can't truly "jump" to positions, this plugin uses **searchable anchors**:

1. Run a teleportation command (e.g., `/cs:top`)
2. The command outputs content with a unique marker like `CS-ANCHOR-TOP`
3. Use your terminal's search (**Ctrl+Shift+F** in most terminals) to find the marker
4. Your terminal scrolls to that exact position

This works with any terminal that supports search (iTerm2, Windows Terminal, VS Code terminal, etc.)

## Data Storage

Claude Code stores conversations in JSONL format:
- **Session files**: `~/.claude/projects/<encoded-path>/<session-id>.jsonl`
- **Global history**: `~/.claude/history.jsonl`

This plugin only reads these local files. No data is sent externally.

## Requirements

- Python 3.8+
- Claude Code installed and used at least once

## Troubleshooting

### Commands not appearing

Make sure you're using the `--plugin-dir` flag:
```bash
claude --plugin-dir /path/to/conversation-search-plugin
```

### "Claude directory not found"

Run Claude Code at least once to create the `~/.claude` directory.

### No sessions found

Check that `~/.claude/projects/` contains your project directories with `.jsonl` files.

## License

MIT License

## Contributing

Issues and pull requests welcome!
