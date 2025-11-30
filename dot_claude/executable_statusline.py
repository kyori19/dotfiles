#!/usr/bin/env python3
"""Claude Code statusline script - displays context, usage, and rate limits."""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# ANSI color codes
CYAN = "\033[36m"
MAGENTA = "\033[35m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

# Cache settings
CACHE_FILE = Path("/tmp/claude_usage_cache.json")
CACHE_TTL = 60  # seconds


def get_color_for_percentage(pct: float) -> str:
    """Return color code based on percentage threshold."""
    if pct >= 80:
        return RED
    elif pct >= 60:
        return YELLOW
    return GREEN


def parse_time_remaining(iso_timestamp: str, is_weekly: bool = False) -> str:
    """Parse ISO timestamp and return human-readable time remaining."""
    try:
        # Handle timezone-aware ISO format
        reset_time = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(reset_time.tzinfo)
        remaining = reset_time - now

        if remaining.total_seconds() <= 0:
            return ""

        total_secs = int(remaining.total_seconds())

        if is_weekly:
            days = total_secs // 86400
            hours = (total_secs % 86400) // 3600
            if days > 0:
                return f"{days}d{hours}h"
            return f"{hours}h"
        else:
            hours = total_secs // 3600
            mins = (total_secs % 3600) // 60
            if hours > 0:
                return f"{hours}h{mins}m"
            return f"{mins}m"
    except Exception:
        return ""


def get_context_usage(transcript_path: str) -> tuple[str, float | None]:
    """Calculate context usage from transcript file."""
    if not transcript_path or not os.path.exists(transcript_path):
        return "N/A", None

    try:
        # Read file in reverse to find last usage entry
        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        last_usage = None
        for line in reversed(lines):
            if '"input_tokens"' in line:
                try:
                    data = json.loads(line)
                    last_usage = data.get("message", {}).get("usage")
                    if last_usage:
                        break
                except json.JSONDecodeError:
                    continue

        if not last_usage:
            return "N/A", None

        input_tokens = last_usage.get("input_tokens", 0)
        cache_read = last_usage.get("cache_read_input_tokens", 0)
        cache_create = last_usage.get("cache_creation_input_tokens", 0)
        api_tokens = input_tokens + cache_read + cache_create

        # Check autoCompactEnabled setting
        claude_config = Path.home() / ".claude.json"
        autocompact_enabled = True
        autocompact_suffix = ""

        if claude_config.exists():
            try:
                with open(claude_config) as f:
                    config = json.load(f)
                    autocompact_enabled = config.get("autoCompactEnabled", True)
            except (json.JSONDecodeError, IOError):
                pass

        if autocompact_enabled:
            autocompact_buffer = 45000
            autocompact_suffix = " (AC)"
        else:
            autocompact_buffer = 0

        total_context = api_tokens + autocompact_buffer
        context_limit = 200000

        if total_context > 0:
            context_pct = (total_context / context_limit) * 100
            return f"{context_pct:.0f}%{autocompact_suffix}", context_pct

        return "N/A", None
    except Exception:
        return "N/A", None


def get_usage_data() -> dict | None:
    """Fetch usage data from API with caching."""
    # Check cache
    if CACHE_FILE.exists():
        cache_age = datetime.now().timestamp() - CACHE_FILE.stat().st_mtime
        if cache_age < CACHE_TTL:
            try:
                with open(CACHE_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

    # Get OAuth token
    creds_file = Path.home() / ".claude" / ".credentials.json"
    if not creds_file.exists():
        return None

    try:
        with open(creds_file) as f:
            creds = json.load(f)
        token = creds.get("claudeAiOauth", {}).get("accessToken")
        if not token:
            return None

        # Fetch from API
        result = subprocess.run(
            [
                "curl", "-s", "--max-time", "3",
                "https://api.anthropic.com/api/oauth/usage",
                "-H", f"Authorization: Bearer {token}",
                "-H", "anthropic-beta: oauth-2025-04-20",
                "-H", "Content-Type: application/json"
            ],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if "five_hour" in data:
                # Cache the response
                with open(CACHE_FILE, 'w') as f:
                    json.dump(data, f)
                return data
    except Exception:
        pass

    return None


def format_usage(data: dict | None, key: str, label: str, is_weekly: bool = False) -> tuple[str, float | None]:
    """Format usage data for display."""
    if not data or key not in data or data[key] is None:
        return "--", None

    usage = data[key]
    pct = usage.get("utilization", 0)
    resets_at = usage.get("resets_at", "")

    time_remaining = parse_time_remaining(resets_at, is_weekly) if resets_at else ""

    if time_remaining:
        return f"{pct:.0f}% ({time_remaining})", pct
    return f"{pct:.0f}%", pct


def main():
    # Read JSON input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}

    # Extract values
    cwd = input_data.get("cwd", "unknown")
    model_name = input_data.get("model", {}).get("display_name", "unknown")
    transcript_path = input_data.get("transcript_path", "")

    # Get context usage
    context_usage, context_pct = get_context_usage(transcript_path)
    context_color = get_color_for_percentage(context_pct) if context_pct else GREEN

    # Get API usage data
    usage_data = get_usage_data()

    # Format 5-hour usage
    five_hour_display, five_hour_pct = format_usage(usage_data, "five_hour", "5h")
    five_hour_color = get_color_for_percentage(five_hour_pct) if five_hour_pct else GREEN

    # Format weekly usage
    weekly_display, weekly_pct = format_usage(usage_data, "seven_day", "7d", is_weekly=True)
    weekly_color = get_color_for_percentage(weekly_pct) if weekly_pct else GREEN

    # Output formatted statusline
    parts = [
        f"{CYAN}{cwd}{RESET}",
        f"{MAGENTA}{model_name}{RESET}",
        f"{context_color}Context: {context_usage}{RESET}",
        f"{five_hour_color}5h: {five_hour_display}{RESET}",
        f"{weekly_color}7d: {weekly_display}{RESET}",
    ]

    print(" | ".join(parts), end="")


if __name__ == "__main__":
    main()
