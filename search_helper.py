#!/usr/bin/env python3
"""
Conversation Search Helper for Claude Code

This script provides search, listing, and analysis functionality for Claude Code
conversation history stored in JSONL format.

Usage:
    python search_helper.py search "query" [options]
    python search_helper.py list-sessions [options]
    python search_helper.py show-session <session_id> [options]
    python search_helper.py recent [options]
    python search_helper.py stats [options]

The script handles large history files efficiently using streaming JSON parsing
and provides rich terminal output with formatting.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple


# ANSI color codes for terminal output
class Colors:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BG_YELLOW = "\033[43m"
    BG_RESET = "\033[49m"


def get_claude_dir() -> Path:
    """Get the Claude Code data directory."""
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        raise FileNotFoundError(f"Claude directory not found: {claude_dir}")
    return claude_dir


def get_projects_dir() -> Path:
    """Get the projects directory containing session files."""
    return get_claude_dir() / "projects"


def get_history_file() -> Path:
    """Get the main history.jsonl file."""
    return get_claude_dir() / "history.jsonl"


def parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse various timestamp formats to datetime."""
    if ts is None:
        return None

    # Handle numeric timestamps (milliseconds)
    if isinstance(ts, (int, float)):
        try:
            # Convert from milliseconds to seconds
            return datetime.fromtimestamp(ts / 1000)
        except (ValueError, OSError):
            return None

    # Handle string timestamps
    if isinstance(ts, str):
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue

    return None


def format_timestamp(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "Unknown"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_relative_time(dt: Optional[datetime]) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')."""
    if dt is None:
        return "Unknown"

    now = datetime.now()
    diff = now - dt

    if diff.days > 365:
        return f"{diff.days // 365} year(s) ago"
    elif diff.days > 30:
        return f"{diff.days // 30} month(s) ago"
    elif diff.days > 0:
        return f"{diff.days} day(s) ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hour(s) ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minute(s) ago"
    else:
        return "Just now"


def stream_jsonl(file_path: Path) -> Generator[Dict[str, Any], None, None]:
    """
    Stream JSONL file line by line for memory efficiency.

    Handles large files by not loading entire file into memory.
    """
    if not file_path.exists():
        return

    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                # Log but continue processing
                print(f"{Colors.DIM}Warning: Skipping malformed JSON at line {line_num}: {e}{Colors.RESET}",
                      file=sys.stderr)
                continue


def get_all_session_files() -> List[Tuple[str, Path, str]]:
    """
    Get all session JSONL files across all projects.

    Returns: List of (project_name, file_path, session_id)
    """
    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        return []

    sessions = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Extract project path from directory name (replace - with /)
        project_name = project_dir.name.replace("-", "/")
        if project_name.startswith("/"):
            project_name = project_name[1:]  # Remove leading slash

        # Find all JSONL session files
        for jsonl_file in project_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            sessions.append((project_name, jsonl_file, session_id))

    return sessions


def extract_message_content(entry: Dict[str, Any]) -> Optional[str]:
    """Extract searchable text content from a JSONL entry."""
    # Handle different entry types
    entry_type = entry.get("type", "")

    if entry_type == "summary":
        return entry.get("summary", "")

    if entry_type == "user":
        message = entry.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", [])
            if isinstance(content, list):
                # Extract text from content blocks
                texts = []
                for block in content:
                    if isinstance(block, dict):
                        if "text" in block:
                            texts.append(block["text"])
                        elif "content" in block:
                            texts.append(str(block["content"]))
                    elif isinstance(block, str):
                        texts.append(block)
                return " ".join(texts)
            elif isinstance(content, str):
                return content
        return str(message) if message else None

    if entry_type == "assistant":
        message = entry.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", [])
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        texts.append(block["text"])
                    elif isinstance(block, str):
                        texts.append(block)
                return " ".join(texts)
            elif isinstance(content, str):
                return content
        return str(message) if message else None

    # For display field (user inputs from history.jsonl)
    if "display" in entry:
        return entry["display"]

    return None


def highlight_matches(text: str, pattern: str, is_regex: bool = False) -> str:
    """Highlight matching text in output."""
    if not pattern:
        return text

    try:
        if is_regex:
            regex = re.compile(pattern, re.IGNORECASE)
        else:
            # Escape special regex characters for literal search
            regex = re.compile(re.escape(pattern), re.IGNORECASE)

        def replacer(match):
            return f"{Colors.BG_YELLOW}{Colors.BOLD}{match.group()}{Colors.RESET}{Colors.BG_RESET}"

        return regex.sub(replacer, text)
    except re.error:
        return text


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "... [truncated]"


# =============================================================================
# SEARCH COMMAND
# =============================================================================

def cmd_search(args: argparse.Namespace) -> int:
    """Execute search across conversation history."""
    query = args.query
    is_regex = args.regex
    project_filter = args.project
    from_date = parse_timestamp(args.from_date) if args.from_date else None
    to_date = parse_timestamp(args.to_date) if args.to_date else None
    context_lines = args.context or 2
    limit = args.limit or 20
    msg_type = args.type

    # Validate regex if provided
    if is_regex:
        try:
            re.compile(query)
        except re.error as e:
            print(f"{Colors.RED}Error: Invalid regex pattern: {e}{Colors.RESET}")
            return 1

    print(f"{Colors.BOLD}## Search Results for: \"{query}\"{Colors.RESET}")
    if is_regex:
        print(f"{Colors.DIM}(regex mode){Colors.RESET}")
    print()

    results = []
    sessions_searched = 0

    # Search through all session files
    sessions = get_all_session_files()

    for project_name, file_path, session_id in sessions:
        # Apply project filter
        if project_filter and project_filter.lower() not in project_name.lower():
            continue

        sessions_searched += 1
        entries = list(stream_jsonl(file_path))

        for idx, entry in enumerate(entries):
            # Apply type filter
            entry_type = entry.get("type", "")
            if msg_type and entry_type != msg_type:
                continue

            # Apply date filter
            timestamp = parse_timestamp(entry.get("timestamp"))
            if from_date and timestamp and timestamp < from_date:
                continue
            if to_date and timestamp and timestamp > to_date:
                continue

            # Search content
            content = extract_message_content(entry)
            if not content:
                continue

            # Match query
            try:
                if is_regex:
                    if not re.search(query, content, re.IGNORECASE):
                        continue
                else:
                    if query.lower() not in content.lower():
                        continue
            except re.error:
                continue

            # Get context (surrounding messages)
            context_before = []
            context_after = []

            for i in range(max(0, idx - context_lines), idx):
                ctx_content = extract_message_content(entries[i])
                if ctx_content:
                    ctx_type = entries[i].get("type", "unknown")
                    context_before.append((ctx_type, truncate_text(ctx_content, 200)))

            for i in range(idx + 1, min(len(entries), idx + context_lines + 1)):
                ctx_content = extract_message_content(entries[i])
                if ctx_content:
                    ctx_type = entries[i].get("type", "unknown")
                    context_after.append((ctx_type, truncate_text(ctx_content, 200)))

            results.append({
                "session_id": session_id,
                "project": project_name,
                "timestamp": timestamp,
                "type": entry_type,
                "content": content,
                "context_before": context_before,
                "context_after": context_after,
            })

            if len(results) >= limit:
                break

        if len(results) >= limit:
            break

    # Also search main history.jsonl
    history_file = get_history_file()
    if history_file.exists() and len(results) < limit:
        for entry in stream_jsonl(history_file):
            # Apply project filter
            entry_project = entry.get("project", "")
            if project_filter and project_filter.lower() not in entry_project.lower():
                continue

            # Apply date filter
            timestamp = parse_timestamp(entry.get("timestamp"))
            if from_date and timestamp and timestamp < from_date:
                continue
            if to_date and timestamp and timestamp > to_date:
                continue

            content = extract_message_content(entry)
            if not content:
                continue

            try:
                if is_regex:
                    if not re.search(query, content, re.IGNORECASE):
                        continue
                else:
                    if query.lower() not in content.lower():
                        continue
            except re.error:
                continue

            results.append({
                "session_id": "history",
                "project": entry_project,
                "timestamp": timestamp,
                "type": "user_input",
                "content": content,
                "context_before": [],
                "context_after": [],
            })

            if len(results) >= limit:
                break

    # Display results
    if not results:
        print(f"{Colors.YELLOW}No matches found.{Colors.RESET}")
        print(f"\n{Colors.DIM}Searched {sessions_searched} sessions.{Colors.RESET}")
        print(f"\n{Colors.DIM}Suggestions:{Colors.RESET}")
        print(f"  - Try broader search terms")
        print(f"  - Remove project filter")
        print(f"  - Expand date range")
        return 0

    print(f"{Colors.GREEN}Found {len(results)} matches across {sessions_searched} sessions{Colors.RESET}")
    print()

    for i, result in enumerate(results, 1):
        print(f"{Colors.BOLD}### Match {i}: Session {result['session_id'][:8]}...{Colors.RESET}")
        print(f"{Colors.CYAN}Project:{Colors.RESET} {result['project']}")
        print(f"{Colors.CYAN}Date:{Colors.RESET} {format_timestamp(result['timestamp'])} ({format_relative_time(result['timestamp'])})")
        print(f"{Colors.CYAN}Type:{Colors.RESET} {result['type']}")
        print()

        # Context before
        for ctx_type, ctx_content in result['context_before']:
            print(f"{Colors.DIM}[{ctx_type}] {ctx_content}{Colors.RESET}")

        # Matching content
        highlighted = highlight_matches(truncate_text(result['content'], 800), query, is_regex)
        print(f"{Colors.GREEN}>>> {Colors.RESET}{highlighted}")

        # Context after
        for ctx_type, ctx_content in result['context_after']:
            print(f"{Colors.DIM}[{ctx_type}] {ctx_content}{Colors.RESET}")

        print()
        print("-" * 60)
        print()

    return 0


# =============================================================================
# LIST-SESSIONS COMMAND
# =============================================================================

def cmd_list_sessions(args: argparse.Namespace) -> int:
    """List all conversation sessions."""
    project_filter = args.project
    from_date = parse_timestamp(args.from_date) if args.from_date else None
    to_date = parse_timestamp(args.to_date) if args.to_date else None
    limit = args.limit or 20
    sort_by = args.sort or "date"

    print(f"{Colors.BOLD}## Conversation Sessions{Colors.RESET}")
    print()

    sessions_data = []

    for project_name, file_path, session_id in get_all_session_files():
        # Apply project filter
        if project_filter and project_filter.lower() not in project_name.lower():
            continue

        # Get session metadata
        entries = list(stream_jsonl(file_path))
        if not entries:
            continue

        # Find timestamps
        timestamps = [parse_timestamp(e.get("timestamp")) for e in entries]
        timestamps = [t for t in timestamps if t is not None]

        if timestamps:
            first_ts = min(timestamps)
            last_ts = max(timestamps)
        else:
            first_ts = None
            last_ts = None

        # Apply date filter
        if from_date and last_ts and last_ts < from_date:
            continue
        if to_date and first_ts and first_ts > to_date:
            continue

        # Get summaries
        summaries = [e.get("summary", "") for e in entries if e.get("type") == "summary"]
        summary_text = summaries[0] if summaries else ""

        # Count messages
        message_count = len([e for e in entries if e.get("type") in ("user", "assistant")])

        # File size
        file_size = file_path.stat().st_size

        sessions_data.append({
            "session_id": session_id,
            "project": project_name,
            "first_ts": first_ts,
            "last_ts": last_ts,
            "message_count": message_count,
            "summary": summary_text,
            "file_size": file_size,
        })

    # Sort sessions
    if sort_by == "date":
        sessions_data.sort(key=lambda x: x["last_ts"] or datetime.min, reverse=True)
    elif sort_by == "size":
        sessions_data.sort(key=lambda x: x["file_size"], reverse=True)
    elif sort_by == "messages":
        sessions_data.sort(key=lambda x: x["message_count"], reverse=True)

    # Apply limit
    sessions_data = sessions_data[:limit]

    if not sessions_data:
        print(f"{Colors.YELLOW}No sessions found matching criteria.{Colors.RESET}")
        return 0

    print(f"{Colors.GREEN}Found {len(sessions_data)} sessions{Colors.RESET}")
    print()

    # Table header
    print(f"{Colors.BOLD}{'Session ID':<12} {'Project':<35} {'Date':<12} {'Msgs':>6} Summary{Colors.RESET}")
    print("-" * 100)

    for session in sessions_data:
        session_short = session["session_id"][:10] + "..."
        project_short = session["project"][-33:] if len(session["project"]) > 35 else session["project"]
        date_str = session["last_ts"].strftime("%Y-%m-%d") if session["last_ts"] else "Unknown"
        summary_short = truncate_text(session["summary"], 40).replace("\n", " ")

        print(f"{session_short:<12} {project_short:<35} {date_str:<12} {session['message_count']:>6} {summary_short}")

    print()
    print(f"{Colors.DIM}Use '/conversation-search:show-session <session_id>' to view full conversation{Colors.RESET}")

    return 0


# =============================================================================
# SHOW-SESSION COMMAND
# =============================================================================

def cmd_show_session(args: argparse.Namespace) -> int:
    """Display full conversation from a session."""
    session_id = args.session_id
    from_msg = args.from_msg or 0
    limit = args.limit
    compact = args.compact
    export_format = args.export

    # Find matching session(s)
    matches = []
    for project_name, file_path, sid in get_all_session_files():
        if session_id.lower() in sid.lower():
            matches.append((project_name, file_path, sid))

    if not matches:
        print(f"{Colors.RED}Error: No session found matching '{session_id}'{Colors.RESET}")
        return 1

    if len(matches) > 1:
        print(f"{Colors.YELLOW}Multiple sessions match '{session_id}':{Colors.RESET}")
        for project, _, sid in matches[:10]:
            print(f"  - {sid} ({project})")
        print(f"\n{Colors.DIM}Please provide a more specific session ID.{Colors.RESET}")
        return 1

    project_name, file_path, full_session_id = matches[0]

    # Load session
    entries = list(stream_jsonl(file_path))

    # Get metadata
    timestamps = [parse_timestamp(e.get("timestamp")) for e in entries]
    timestamps = [t for t in timestamps if t is not None]
    first_ts = min(timestamps) if timestamps else None
    last_ts = max(timestamps) if timestamps else None

    git_branch = None
    for e in entries:
        if "gitBranch" in e:
            git_branch = e["gitBranch"]
            break

    # Filter to messages only
    messages = [e for e in entries if e.get("type") in ("user", "assistant")]

    # Export if requested
    if export_format:
        return export_session(full_session_id, project_name, entries, messages, export_format, first_ts, last_ts, git_branch)

    # Display header
    print(f"{Colors.BOLD}## Session: {full_session_id}{Colors.RESET}")
    print(f"{Colors.CYAN}Project:{Colors.RESET} {project_name}")
    if first_ts and last_ts:
        duration = last_ts - first_ts
        print(f"{Colors.CYAN}Date:{Colors.RESET} {format_timestamp(first_ts)} - {format_timestamp(last_ts)} ({duration})")
    if git_branch:
        print(f"{Colors.CYAN}Branch:{Colors.RESET} {git_branch}")
    print(f"{Colors.CYAN}Messages:{Colors.RESET} {len(messages)}")
    print()
    print("-" * 60)
    print()

    # Apply pagination
    messages_to_show = messages[from_msg:]
    if limit:
        messages_to_show = messages_to_show[:limit]

    for _, entry in enumerate(messages_to_show, from_msg + 1):
        msg_type = entry.get("type", "unknown")
        timestamp = parse_timestamp(entry.get("timestamp"))
        content = extract_message_content(entry) or ""

        # Format header
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else ""
        type_color = Colors.BLUE if msg_type == "user" else Colors.GREEN

        print(f"{type_color}{Colors.BOLD}### {msg_type.title()} ({time_str}){Colors.RESET}")

        # Format content
        if compact:
            content = truncate_text(content, 500)

        print(content)
        print()

    if len(messages) > from_msg + len(messages_to_show):
        remaining = len(messages) - from_msg - len(messages_to_show)
        print(f"{Colors.DIM}... {remaining} more messages. Use --from-msg {from_msg + len(messages_to_show)} to continue.{Colors.RESET}")

    return 0


def export_session(
    session_id: str,
    project: str,
    entries: List[Dict],
    messages: List[Dict],
    format: str,
    first_ts: Optional[datetime],
    last_ts: Optional[datetime],
    git_branch: Optional[str]
) -> int:
    """Export session in specified format."""

    if format == "json":
        output = {
            "session_id": session_id,
            "project": project,
            "first_timestamp": first_ts.isoformat() if first_ts else None,
            "last_timestamp": last_ts.isoformat() if last_ts else None,
            "git_branch": git_branch,
            "entries": entries,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        return 0

    if format == "markdown":
        lines = [
            f"# Session: {session_id}",
            "",
            f"**Project:** {project}",
            f"**Date:** {format_timestamp(first_ts)} - {format_timestamp(last_ts)}",
            f"**Branch:** {git_branch or 'N/A'}",
            f"**Messages:** {len(messages)}",
            "",
            "---",
            "",
        ]

        for entry in messages:
            msg_type = entry.get("type", "unknown")
            timestamp = parse_timestamp(entry.get("timestamp"))
            content = extract_message_content(entry) or ""
            time_str = timestamp.strftime("%H:%M:%S") if timestamp else ""

            lines.append(f"## {msg_type.title()} ({time_str})")
            lines.append("")
            lines.append(content)
            lines.append("")

        print("\n".join(lines))
        return 0

    if format == "text":
        lines = [
            f"Session: {session_id}",
            f"Project: {project}",
            f"Date: {format_timestamp(first_ts)} - {format_timestamp(last_ts)}",
            f"Branch: {git_branch or 'N/A'}",
            f"Messages: {len(messages)}",
            "",
            "=" * 60,
            "",
        ]

        for entry in messages:
            msg_type = entry.get("type", "unknown")
            timestamp = parse_timestamp(entry.get("timestamp"))
            content = extract_message_content(entry) or ""
            time_str = timestamp.strftime("%H:%M:%S") if timestamp else ""

            lines.append(f"[{msg_type.upper()}] {time_str}")
            lines.append(content)
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        print("\n".join(lines))
        return 0

    print(f"{Colors.RED}Error: Unknown export format '{format}'. Use: markdown, json, text{Colors.RESET}")
    return 1


# =============================================================================
# RECENT COMMAND
# =============================================================================

def cmd_recent(args: argparse.Namespace) -> int:
    """Show recent conversations."""
    hours = args.hours or 24
    if args.days:
        hours = args.days * 24
    project_filter = args.project
    summary_only = args.summary_only

    cutoff = datetime.now() - timedelta(hours=hours)

    print(f"{Colors.BOLD}## Recent Conversations (last {hours} hours){Colors.RESET}")
    print()

    # Collect recent activity
    recent_activity = []

    for project_name, file_path, session_id in get_all_session_files():
        if project_filter and project_filter.lower() not in project_name.lower():
            continue

        entries = list(stream_jsonl(file_path))

        # Find latest timestamp
        timestamps = [parse_timestamp(e.get("timestamp")) for e in entries]
        timestamps = [t for t in timestamps if t is not None]

        if not timestamps:
            continue

        last_ts = max(timestamps)

        if last_ts < cutoff:
            continue

        # Get summary
        summaries = [e.get("summary", "") for e in entries if e.get("type") == "summary"]
        summary = summaries[0] if summaries else "No summary"

        # Get message count
        message_count = len([e for e in entries if e.get("type") in ("user", "assistant")])

        # Get short project name
        project_short = project_name.split("/")[-1] if "/" in project_name else project_name

        recent_activity.append({
            "session_id": session_id,
            "project": project_name,
            "project_short": project_short,
            "timestamp": last_ts,
            "summary": summary,
            "message_count": message_count,
        })

    # Sort by timestamp
    recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)

    if not recent_activity:
        print(f"{Colors.YELLOW}No recent activity found in the last {hours} hours.{Colors.RESET}")
        return 0

    # Group by day
    grouped = defaultdict(list)
    today = datetime.now().date()

    for activity in recent_activity:
        activity_date = activity["timestamp"].date()
        if activity_date == today:
            day_label = "Today"
        elif activity_date == today - timedelta(days=1):
            day_label = "Yesterday"
        else:
            days_ago = (today - activity_date).days
            day_label = f"{days_ago} days ago"

        grouped[day_label].append(activity)

    # Display
    for day_label in ["Today", "Yesterday"] + sorted([k for k in grouped.keys() if k not in ["Today", "Yesterday"]]):
        if day_label not in grouped:
            continue

        print(f"{Colors.BOLD}### {day_label}{Colors.RESET}")

        for activity in grouped[day_label]:
            time_str = activity["timestamp"].strftime("%H:%M")
            summary_short = truncate_text(activity["summary"], 60).replace("\n", " ")

            print(f"- {Colors.CYAN}{time_str}{Colors.RESET} [{activity['project_short']}] {summary_short}")

            if not summary_only:
                print(f"  {Colors.DIM}Session: {activity['session_id'][:12]}... | {activity['message_count']} messages{Colors.RESET}")

        print()

    return 0


# =============================================================================
# STATS COMMAND
# =============================================================================

def cmd_stats(args: argparse.Namespace) -> int:
    """Show conversation statistics."""
    project_filter = args.project
    from_date = parse_timestamp(args.from_date) if args.from_date else None
    to_date = parse_timestamp(args.to_date) if args.to_date else None
    _detailed = args.detailed  # Reserved for future detailed stats output

    print(f"{Colors.BOLD}## Conversation Statistics{Colors.RESET}")
    print()

    # Collect stats
    total_sessions = 0
    total_messages = 0
    total_size = 0
    all_timestamps: List[datetime] = []
    project_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"sessions": 0, "messages": 0, "last_active": None})
    day_of_week_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"sessions": 0, "messages": 0})
    summary_words = defaultdict(int)

    for project_name, file_path, _ in get_all_session_files():
        if project_filter and project_filter.lower() not in project_name.lower():
            continue

        entries = list(stream_jsonl(file_path))
        if not entries:
            continue

        timestamps = [parse_timestamp(e.get("timestamp")) for e in entries]
        timestamps = [t for t in timestamps if t is not None]

        if timestamps:
            last_ts = max(timestamps)
            first_ts = min(timestamps)

            # Apply date filter
            if from_date and last_ts < from_date:
                continue
            if to_date and first_ts > to_date:
                continue

            all_timestamps.extend(timestamps)

            # Day of week stats
            for ts in timestamps:
                day_name = ts.strftime("%A")
                day_of_week_stats[day_name]["messages"] += 1
        else:
            last_ts = None

        message_count = len([e for e in entries if e.get("type") in ("user", "assistant")])
        file_size = file_path.stat().st_size

        total_sessions += 1
        total_messages += message_count
        total_size += file_size

        # Project stats
        project_short = project_name.split("/")[-1] if "/" in project_name else project_name
        ps = project_stats[project_short]
        ps["sessions"] = int(ps["sessions"]) + 1
        ps["messages"] = int(ps["messages"]) + message_count
        current_last_active = ps["last_active"]
        if last_ts and (current_last_active is None or
                        (isinstance(current_last_active, datetime) and last_ts > current_last_active)):
            ps["last_active"] = last_ts

        day_of_week_stats[last_ts.strftime("%A") if last_ts else "Unknown"]["sessions"] += 1

        # Extract summary words
        for e in entries:
            if e.get("type") == "summary":
                summary = e.get("summary", "")
                words = re.findall(r'\b\w+\b', summary.lower())
                for word in words:
                    if len(word) > 4 and word not in ("about", "their", "there", "these", "would", "could", "should"):
                        summary_words[word] += 1

    # Display overview
    print(f"{Colors.BOLD}### Overview{Colors.RESET}")
    print(f"- {Colors.CYAN}Total Sessions:{Colors.RESET} {total_sessions}")
    print(f"- {Colors.CYAN}Total Messages:{Colors.RESET} {total_messages:,}")
    print(f"- {Colors.CYAN}History Size:{Colors.RESET} {total_size / (1024*1024):.1f} MB")

    if all_timestamps:
        first_date = min(all_timestamps)
        last_date = max(all_timestamps)
        print(f"- {Colors.CYAN}Date Range:{Colors.RESET} {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}")

    print()

    # Projects stats
    print(f"{Colors.BOLD}### Projects (Top 10){Colors.RESET}")
    sorted_projects = sorted(project_stats.items(), key=lambda x: int(x[1]["messages"] or 0), reverse=True)[:10]

    print(f"{'Project':<30} {'Sessions':>10} {'Messages':>10} {'Last Active':>15}")
    print("-" * 70)

    for project, stats in sorted_projects:
        last_active = format_relative_time(stats["last_active"]) if stats["last_active"] else "Unknown"
        project_display = project[-28:] if len(project) > 30 else project
        print(f"{project_display:<30} {stats['sessions']:>10} {stats['messages']:>10} {last_active:>15}")

    print()

    # Day of week stats
    print(f"{Colors.BOLD}### Activity by Day of Week{Colors.RESET}")
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    print(f"{'Day':<12} {'Sessions':>10} {'Messages':>12}")
    print("-" * 40)

    for day in day_order:
        if day in day_of_week_stats:
            stats = day_of_week_stats[day]
            print(f"{day:<12} {stats['sessions']:>10} {stats['messages']:>12}")

    print()

    # Common topics
    print(f"{Colors.BOLD}### Common Topics (from summaries){Colors.RESET}")
    sorted_words = sorted(summary_words.items(), key=lambda x: x[1], reverse=True)[:10]

    for i, (word, count) in enumerate(sorted_words, 1):
        print(f"{i}. \"{word}\" ({count} occurrences)")

    return 0


# =============================================================================
# TELEPORTATION COMMANDS
# =============================================================================

# Unique searchable anchors - use Ctrl+Shift+F in terminal to find these
ANCHOR_START = "═══════════════════════════════════════════════════════════════════════════════"
ANCHOR_MARKER = "▶▶▶ CS-ANCHOR"
ANCHOR_END = "═══════════════════════════════════════════════════════════════════════════════"


def get_current_session_file() -> Optional[Path]:
    """Find the current session's JSONL file based on CWD."""
    cwd = Path.cwd()
    projects_dir = get_projects_dir()

    # Encode current path to match Claude's format
    cwd_encoded = str(cwd).replace("/", "-")
    if cwd_encoded.startswith("-"):
        cwd_encoded = cwd_encoded[1:]  # Remove leading dash

    project_dir = projects_dir / f"-{cwd_encoded}"
    if not project_dir.exists():
        # Try partial match
        for d in projects_dir.iterdir():
            if d.is_dir() and cwd.name in d.name:
                project_dir = d
                break

    if not project_dir.exists():
        return None

    # Find most recent session file
    session_files = list(project_dir.glob("*.jsonl"))
    if not session_files:
        return None

    # Sort by modification time, newest first
    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return session_files[0]


def cmd_top(args: argparse.Namespace) -> int:
    """Show the beginning of the current conversation with searchable anchor."""
    limit = args.limit if hasattr(args, 'limit') and args.limit else 5

    session_file = get_current_session_file()
    if not session_file:
        print(f"{Colors.RED}Could not find current session file.{Colors.RESET}")
        print(f"{Colors.DIM}Make sure you're in a project directory with Claude history.{Colors.RESET}")
        return 1

    entries = list(stream_jsonl(session_file))
    if not entries:
        print(f"{Colors.RED}No entries found in session.{Colors.RESET}")
        return 1

    # Get first few messages
    messages = [e for e in entries if e.get("type") in ("user", "assistant")][:limit]

    # Get session metadata
    first_entry = entries[0]
    session_id = first_entry.get("sessionId", session_file.stem[:8])
    first_ts = parse_timestamp(first_entry.get("timestamp"))

    # Output searchable anchor
    print(f"\n{Colors.CYAN}{ANCHOR_START}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{ANCHOR_MARKER}-TOP: CONVERSATION START{Colors.RESET}")
    print(f"{Colors.CYAN}{ANCHOR_START}{Colors.RESET}\n")

    print(f"{Colors.BOLD}Session:{Colors.RESET} {session_id}")
    print(f"{Colors.BOLD}Started:{Colors.RESET} {format_timestamp(first_ts)}")
    print(f"{Colors.BOLD}File:{Colors.RESET} {session_file}")
    print()

    # Show first messages
    print(f"{Colors.BOLD}First {len(messages)} messages:{Colors.RESET}\n")

    for entry in messages:
        msg_type = entry.get("type", "unknown")
        content = extract_message_content(entry) or ""
        timestamp = parse_timestamp(entry.get("timestamp"))

        type_color = Colors.BLUE if msg_type == "user" else Colors.GREEN
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else ""

        print(f"{type_color}{Colors.BOLD}[{msg_type.upper()}] {time_str}{Colors.RESET}")

        # Truncate long messages
        if len(content) > 500:
            content = content[:500] + "... [truncated]"
        print(f"{content}\n")

    print(f"{Colors.DIM}Use Ctrl+Shift+F and search '{ANCHOR_MARKER}-TOP' to find this anchor{Colors.RESET}")
    return 0


def cmd_pre_compact(args: argparse.Namespace) -> int:
    """Show content from before the last compaction/summarization."""
    session_file = get_current_session_file()
    if not session_file:
        print(f"{Colors.RED}Could not find current session file.{Colors.RESET}")
        return 1

    entries = list(stream_jsonl(session_file))
    if not entries:
        print(f"{Colors.RED}No entries found in session.{Colors.RESET}")
        return 1

    # Find summary entries (these mark compaction points)
    summaries = [(i, e) for i, e in enumerate(entries) if e.get("type") == "summary"]

    if not summaries:
        print(f"{Colors.YELLOW}No compaction points found in this session.{Colors.RESET}")
        print(f"{Colors.DIM}The conversation hasn't been summarized yet.{Colors.RESET}")
        return 0

    # Get the last summary (most recent compaction)
    last_summary_idx, last_summary = summaries[-1]

    # Output searchable anchor
    print(f"\n{Colors.CYAN}{ANCHOR_START}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{ANCHOR_MARKER}-PRECOMPACT: BEFORE LAST SUMMARIZATION{Colors.RESET}")
    print(f"{Colors.CYAN}{ANCHOR_START}{Colors.RESET}\n")

    print(f"{Colors.BOLD}Compaction Points Found:{Colors.RESET} {len(summaries)}")
    print(f"{Colors.BOLD}Last Summary:{Colors.RESET} {last_summary.get('summary', 'No summary text')[:200]}")
    print()

    # Find messages before this summary
    context_before = args.context if hasattr(args, 'context') and args.context else 10

    # Get messages before the summary
    pre_compact_entries = []
    for i in range(max(0, last_summary_idx - context_before), last_summary_idx):
        if entries[i].get("type") in ("user", "assistant"):
            pre_compact_entries.append(entries[i])

    if not pre_compact_entries:
        print(f"{Colors.YELLOW}No messages found before compaction.{Colors.RESET}")
        return 0

    print(f"{Colors.BOLD}Messages before last compaction ({len(pre_compact_entries)}):{Colors.RESET}\n")

    for entry in pre_compact_entries:
        msg_type = entry.get("type", "unknown")
        content = extract_message_content(entry) or ""
        timestamp = parse_timestamp(entry.get("timestamp"))

        type_color = Colors.BLUE if msg_type == "user" else Colors.GREEN
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else ""

        print(f"{type_color}{Colors.BOLD}[{msg_type.upper()}] {time_str}{Colors.RESET}")

        if len(content) > 800:
            content = content[:800] + "... [truncated]"
        print(f"{content}\n")

    print(f"{Colors.DIM}Use Ctrl+Shift+F and search '{ANCHOR_MARKER}-PRECOMPACT' to find this anchor{Colors.RESET}")
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    """Quick keyword search in current session."""
    keyword = args.keyword
    limit = args.limit if hasattr(args, 'limit') and args.limit else 10

    session_file = get_current_session_file()
    if not session_file:
        print(f"{Colors.RED}Could not find current session file.{Colors.RESET}")
        return 1

    entries = list(stream_jsonl(session_file))
    messages = [e for e in entries if e.get("type") in ("user", "assistant")]

    if not messages:
        print(f"{Colors.RED}No messages found in session.{Colors.RESET}")
        return 1

    # Search for keyword
    matches = []
    for i, entry in enumerate(messages):
        content = extract_message_content(entry) or ""
        if keyword.lower() in content.lower():
            matches.append((i, entry, content))

    if not matches:
        print(f"{Colors.YELLOW}No matches found for '{keyword}'{Colors.RESET}")
        return 0

    # Output searchable anchor
    print(f"\n{Colors.CYAN}{ANCHOR_START}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{ANCHOR_MARKER}-FIND: '{keyword}'{Colors.RESET}")
    print(f"{Colors.CYAN}{ANCHOR_START}{Colors.RESET}\n")

    print(f"{Colors.GREEN}Found {len(matches)} matches for '{keyword}'{Colors.RESET}\n")

    # Show matches with context
    for match_num, (_, entry, content) in enumerate(matches[:limit], 1):
        msg_type = entry.get("type", "unknown")
        timestamp = parse_timestamp(entry.get("timestamp"))

        print(f"{Colors.BOLD}Match {match_num}/{min(len(matches), limit)}{Colors.RESET}")

        type_color = Colors.BLUE if msg_type == "user" else Colors.GREEN
        time_str = format_timestamp(timestamp)

        print(f"{type_color}[{msg_type.upper()}] {time_str}{Colors.RESET}")

        # Highlight keyword in content
        highlighted = highlight_matches(content, keyword)
        # Truncate if too long
        if len(highlighted) > 500:
            highlighted = highlighted[:500] + "..."
        print(f"{highlighted}\n")
        print("-" * 60)
        print()

    if len(matches) > limit:
        print(f"{Colors.DIM}Showing {limit} of {len(matches)} matches. Use --limit to see more.{Colors.RESET}")

    print(f"{Colors.DIM}Use Ctrl+Shift+F and search '{ANCHOR_MARKER}-FIND' to find this anchor{Colors.RESET}")
    return 0


def cmd_anchor(args: argparse.Namespace) -> int:
    """Output a searchable marker at current position."""
    label = args.label if hasattr(args, 'label') and args.label else datetime.now().strftime("%H%M%S")

    print(f"\n{Colors.MAGENTA}{ANCHOR_START}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{ANCHOR_MARKER}-{label.upper()}{Colors.RESET}")
    print(f"{Colors.BOLD}Time:{Colors.RESET} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Colors.MAGENTA}{ANCHOR_START}{Colors.RESET}\n")

    print(f"{Colors.DIM}Anchor '{label}' placed. Search '{ANCHOR_MARKER}-{label.upper()}' to return here.{Colors.RESET}")
    return 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Search and analyze Claude Code conversation history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search "python async" --project manufacturing
  %(prog)s search "Error.*failed" --regex --from 2025-01-01
  %(prog)s list-sessions --sort messages --limit 10
  %(prog)s show-session abc123 --compact
  %(prog)s recent --days 7
  %(prog)s stats --detailed
        """
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search conversation history")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--project", "-p", help="Filter by project path")
    search_parser.add_argument("--regex", "-r", action="store_true", help="Treat query as regex")
    search_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    search_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    search_parser.add_argument("--context", "-c", type=int, help="Context lines (default 2)")
    search_parser.add_argument("--limit", "-l", type=int, help="Max results (default 20)")
    search_parser.add_argument("--type", "-t", choices=["user", "assistant", "summary"], help="Message type filter")

    # List sessions command
    list_parser = subparsers.add_parser("list-sessions", help="List conversation sessions")
    list_parser.add_argument("--project", "-p", help="Filter by project path")
    list_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    list_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    list_parser.add_argument("--limit", "-l", type=int, help="Max sessions (default 20)")
    list_parser.add_argument("--sort", "-s", choices=["date", "size", "messages"], help="Sort by (default date)")

    # Show session command
    show_parser = subparsers.add_parser("show-session", help="Show full session")
    show_parser.add_argument("session_id", help="Session ID (partial match)")
    show_parser.add_argument("--from-msg", type=int, help="Start from message number")
    show_parser.add_argument("--limit", "-l", type=int, help="Number of messages")
    show_parser.add_argument("--compact", action="store_true", help="Truncate long messages")
    show_parser.add_argument("--export", "-e", choices=["markdown", "json", "text"], help="Export format")

    # Recent command
    recent_parser = subparsers.add_parser("recent", help="Show recent conversations")
    recent_parser.add_argument("--hours", type=int, help="Hours to look back (default 24)")
    recent_parser.add_argument("--days", type=int, help="Days to look back")
    recent_parser.add_argument("--project", "-p", help="Filter by project path")
    recent_parser.add_argument("--summary-only", action="store_true", help="Show only summaries")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--project", "-p", help="Filter by project path")
    stats_parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    stats_parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    stats_parser.add_argument("--detailed", "-d", action="store_true", help="Show detailed breakdown")

    # === TELEPORTATION COMMANDS ===

    # Top command - jump to conversation start
    top_parser = subparsers.add_parser("top", help="Jump to conversation start with searchable anchor")
    top_parser.add_argument("--limit", "-l", type=int, default=5, help="Number of messages to show (default 5)")

    # Pre-compact command - show before last compaction
    precompact_parser = subparsers.add_parser("pre-compact", help="Show content before last compaction")
    precompact_parser.add_argument("--context", "-c", type=int, default=10, help="Messages before compaction (default 10)")

    # Find command - quick keyword search
    find_parser = subparsers.add_parser("find", help="Quick keyword search in current session")
    find_parser.add_argument("keyword", help="Keyword to search for")
    find_parser.add_argument("--limit", "-l", type=int, default=10, help="Max results (default 10)")

    # Anchor command - place a searchable marker
    anchor_parser = subparsers.add_parser("anchor", help="Place a searchable marker")
    anchor_parser.add_argument("label", nargs="?", default=None, help="Custom label for anchor (optional)")

    args = parser.parse_args()

    try:
        if args.command == "search":
            return cmd_search(args)
        elif args.command == "list-sessions":
            return cmd_list_sessions(args)
        elif args.command == "show-session":
            return cmd_show_session(args)
        elif args.command == "recent":
            return cmd_recent(args)
        elif args.command == "stats":
            return cmd_stats(args)
        # Teleportation commands
        elif args.command == "top":
            return cmd_top(args)
        elif args.command == "pre-compact":
            return cmd_pre_compact(args)
        elif args.command == "find":
            return cmd_find(args)
        elif args.command == "anchor":
            return cmd_anchor(args)
        else:
            parser.print_help()
            return 1
    except FileNotFoundError as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        return 1
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Search cancelled.{Colors.RESET}")
        return 130


if __name__ == "__main__":
    sys.exit(main())
