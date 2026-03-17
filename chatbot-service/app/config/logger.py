"""
ChatBot Logger — structured request logging for the agent pipeline.

Produces human-readable, section-based log files following the format:
  ═══════════════════
  REQUEST_ID / USER_ID / CONVERSATION_ID / TIMESTAMP
  ═══════════════════
    SECTION NAME
  ═══════════════════
    key: value
  ...
  REQUEST <id> COMPLETED AT <timestamp>
  ═══════════════════

Usage:
    from ..config.logger import ChatBotLogger

    log = ChatBotLogger(request_id=..., user_id=..., conversation_id=...)
    log.start_request()
    log.log_section("INTENT CLASSIFIER", user_message=msg, ...)
    log.end_request()
"""

import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from typing import Any, List, Optional, Union


# ── Directory setup ──────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).parent.parent / "logs" / "chat_bot_logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_SEPARATOR = "=" * 100


def _get_file_logger() -> logging.Logger:
    """Return (or create) the shared file-backed logger."""
    name = "chatbot.request_logger"
    logger = logging.getLogger(name)

    if not logger.handlers:
        log_file = _LOG_DIR / "chatbot.log"
        handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=30,       # keep 30 days of logs
            encoding="utf-8",
        )
        handler.suffix = "%Y-%m-%d"
        # Raw formatter — the ChatBotLogger builds its own pretty output
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


class ChatBotLogger:
    """
    Per-request logger that writes structured sections to the chatbot log file.

    Instantiate one at the start of each request, call ``log_section`` for
    every agent step, and ``end_request`` when done.
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[Union[int, str]] = None,
        conversation_id: Optional[Union[int, str]] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = str(user_id) if user_id is not None else "N/A"
        self.conversation_id = str(conversation_id) if conversation_id is not None else "N/A"
        self.start_time = datetime.now(timezone.utc)
        self._logger = _get_file_logger()

    # ── public API ───────────────────────────────────────────────────────

    def start_request(self) -> None:
        """Log the request header block."""
        lines = [
            "",
            _SEPARATOR,
            "",
            f"REQUEST_ID:       {self.request_id}",
            f"USER_ID:          {self.user_id}",
            f"CONVERSATION_ID:  {self.conversation_id}",
            f"TIMESTAMP:        {self.start_time.isoformat()}",
            "",
        ]
        self._write(lines)

    def log_section(self, title: str, **kwargs: Any) -> None:
        """
        Log a named section with arbitrary key-value data.

        Example::

            log.log_section(
                "INTENT CLASSIFIER",
                user_message="hello",
                classification_result={"intent": "chitchat", ...},
            )
        """
        lines = [
            _SEPARATOR,
            f"  {title}",
            _SEPARATOR,
            "",
        ]
        for key, value in kwargs.items():
            label = _pretty_label(key)
            formatted = _format_value(value)
            lines.append(f"  {label:<22}{formatted}")
        lines.append("")
        self._write(lines)

    def log_db_rows(
        self,
        title: str,
        rows: List[dict],
        fields: Optional[List[str]] = None,
        max_rows: int = 10,
    ) -> None:
        """
        Log candidate rows retrieved from the database in a readable table.

        Args:
            title:    Section heading (e.g. "FILTER - DB ROWS").
            rows:     List of row dicts from the query.
            fields:   Which keys to display. Defaults to the most useful ones.
            max_rows: Maximum rows to print (rest are summarised).
        """
        if fields is None:
            fields = [
                "full_name", "applied_position", "nationality",
                "years_of_experience", "expected_salary_remote", "expected_salary_onsite",
                "current_address",
            ]

        lines = [
            _SEPARATOR,
            f"  {title}",
            _SEPARATOR,
            "",
            f"  Total Rows:         {len(rows)}",
            "",
        ]

        display = rows[:max_rows]
        for i, row in enumerate(display, 1):
            parts = []
            for f in fields:
                val = row.get(f)
                if val is not None and val != "":
                    label = f.replace("_", " ").title()
                    parts.append(f"{label}: {val}")
            lines.append(f"    {i}. {' | '.join(parts)}")

        if len(rows) > max_rows:
            lines.append(f"    ... and {len(rows) - max_rows} more rows")

        lines.append("")
        self._write(lines)

    def log_db_stats(
        self,
        title: str,
        stats: List[dict],
    ) -> None:
        """
        Log aggregation statistics returned from the database.

        Args:
            title: Section heading (e.g. "AGGREGATION - DB STATS").
            stats: List of stat-row dicts from the query.
        """
        lines = [
            _SEPARATOR,
            f"  {title}",
            _SEPARATOR,
            "",
        ]

        if not stats:
            lines.append("  (no statistics returned)")
        else:
            for row in stats:
                for key, val in row.items():
                    label = key.replace("_", " ").title() + ":"
                    lines.append(f"    {label:<30}{val}")
                lines.append("")

        lines.append("")
        self._write(lines)

    def end_request(self) -> None:
        """Log the request completion footer."""
        end_time = datetime.now(timezone.utc)
        lines = [
            f"REQUEST {self.request_id} COMPLETED AT {end_time.isoformat()}",
            _SEPARATOR,
            "",
        ]
        self._write(lines)

    # ── internals ────────────────────────────────────────────────────────

    def _write(self, lines: List[str]) -> None:
        self._logger.info("\n".join(lines))


# ── Formatting helpers ───────────────────────────────────────────────────────

def _pretty_label(key: str) -> str:
    """Convert snake_case key to Title Case Label:"""
    return key.replace("_", " ").title() + ":"


def _format_value(value: Any) -> str:
    """
    Return a string representation of *value*.

    - Dicts and lists are rendered with indented sub-keys.
    - Long strings are kept as-is (the log is meant to be read as plain text).
    """
    if value is None:
        return "N/A"

    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = []
        for k, v in value.items():
            parts.append(f"\n    {_pretty_label(k):<20}{v}")
        return "".join(parts)

    if isinstance(value, list):
        if not value:
            return "[]"
        if len(value) <= 5:
            parts = []
            for i, item in enumerate(value, 1):
                parts.append(f"\n    {i}. {_compact(item)}")
            return "".join(parts)
        # Truncate long lists
        parts = []
        for i, item in enumerate(value[:5], 1):
            parts.append(f"\n    {i}. {_compact(item)}")
        parts.append(f"\n    ... and {len(value) - 5} more")
        return "".join(parts)

    text = str(value)
    # Truncate very long text to keep logs readable
    if len(text) > 500:
        text = text[:500] + "..."
    return text


def _compact(item: Any) -> str:
    """One-line representation of a list item."""
    if isinstance(item, dict):
        pairs = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:4])
        if len(item) > 4:
            pairs += ", ..."
        return f"{{{pairs}}}"
    text = str(item)
    if len(text) > 200:
        text = text[:200] + "..."
    return text
