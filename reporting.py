from __future__ import annotations

import platform
import re
from urllib.parse import urlencode

from app_info import APP_VERSION, BUG_REPORT_URL


_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"AIza[0-9A-Za-z_-]{20,}"), "[REDACTED]"),
    (
        re.compile(r"\bAQ\.[0-9A-Za-z._-]{12,}\b", re.IGNORECASE),
        "[REDACTED]",
    ),
    (
        re.compile(
            r"(?i)((?:gemini_)?api[_ -]?key\s*[=:]\s*)[^\s&]+",
        ),
        r"\1[REDACTED]",
    ),
)


def redact_secrets(value: str) -> str:
    safe = str(value or "")
    for pattern, replacement in _SECRET_PATTERNS:
        safe = pattern.sub(replacement, safe)
    return safe


def build_bug_report_url(
    source: str,
    error_detail: str = "",
) -> str:
    safe_source = redact_secrets(source).strip() or "Nova Lens"
    safe_error = redact_secrets(error_detail).strip()
    if len(safe_error) > 1200:
        safe_error = safe_error[:1200] + "…"

    body_parts = [
        "## What happened?",
        "<!-- Describe the problem and what you expected instead. -->",
        "",
        "## Steps to reproduce",
        "1. ",
        "2. ",
        "3. ",
        "",
        "## Nova Lens information",
        f"- Version: {APP_VERSION}",
        f"- Source: {safe_source}",
        f"- System: {platform.system()} {platform.release()}",
    ]

    if safe_error:
        body_parts.extend(
            [
                "",
                "## Error shown by Nova Lens",
                "```text",
                safe_error,
                "```",
            ]
        )

    body_parts.extend(
        [
            "",
            "## Additional context",
            "<!-- Add screenshots if useful. Never include your API key. -->",
        ]
    )

    query = urlencode(
        {
            "title": "[Bug] ",
            "body": "\n".join(body_parts),
        }
    )
    return f"{BUG_REPORT_URL}?{query}"
