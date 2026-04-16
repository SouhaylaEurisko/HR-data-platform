"""Pure value coercion helpers for XLSX import row mapping."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from ..models.enums import RelocationOpenness, TransportationAvailability


def to_json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def normalize_numeric_string_to_decimal_str(cleaned: str) -> Optional[str]:
    """
    Turn a cleaned string (digits, optional . and , and leading -) into a form
    Decimal() accepts.
    """
    s = cleaned.strip()
    if not s:
        return None
    neg = False
    if s.startswith("-"):
        neg = True
        s = s[1:]
    if not s or not re.fullmatch(r"[\d\.,]+", s):
        return None

    def with_sign(num: str) -> str:
        return ("-" if neg else "") + num

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            num = s.replace(".", "").replace(",", ".")
        else:
            num = s.replace(",", "")
        return with_sign(num)

    if "," in s:
        parts = s.split(",")
        if len(parts) > 1 and len(parts[-1]) <= 2:
            num = "".join(parts[:-1]) + "." + parts[-1]
        else:
            num = "".join(parts)
        return with_sign(num)

    if "." in s:
        parts = s.split(".")
        if len(parts) >= 2 and all(len(p) == 3 for p in parts[1:]):
            return with_sign("".join(parts))
        return with_sign(s)

    return with_sign(s)


def to_decimal_or_none(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = str(value).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^0-9\.,\-]", "", text)
    if not cleaned:
        return None
    range_match = re.match(r"^([\d\.,]+)\s*[-–]\s*([\d\.,]+)$", cleaned)
    if range_match:
        cleaned = range_match.group(1)
    normalized = normalize_numeric_string_to_decimal_str(cleaned)
    if not normalized:
        return None
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def to_date_or_none(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def to_bool_or_none(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "yes", "y", "employed"):
        return True
    if text in ("false", "no", "n", "unemployed", "not employed"):
        return False
    return None


def to_relocation_openness_or_none(value: Any) -> Optional[RelocationOpenness]:
    if value is None:
        return None
    if isinstance(value, RelocationOpenness):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    if "mission" in text:
        return RelocationOpenness.for_missions_only
    if text in ("true", "yes", "y"):
        return RelocationOpenness.yes
    if text in ("false", "no", "n"):
        return RelocationOpenness.no
    for member in RelocationOpenness:
        if text == member.value or text == member.name.lower():
            return member
    return None


def to_transportation_availability_or_none(value: Any) -> Optional[TransportationAvailability]:
    if value is None:
        return None
    if isinstance(value, TransportationAvailability):
        return value
    text = str(value).strip().lower()
    if not text:
        return None
    for member in TransportationAvailability:
        if text == member.value or text == member.name.lower():
            return member
    if text in ("true", "yes", "has transportation", "has car", "own vehicle"):
        return TransportationAvailability.yes
    if text in ("false", "no", "no transportation"):
        return TransportationAvailability.no
    if "only" in text and "remote" in text:
        return TransportationAvailability.only_open_for_remote_opportunities
    if "remote only" in text or "remote opportunities" in text:
        return TransportationAvailability.only_open_for_remote_opportunities
    return None


def to_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    months_match = re.match(r"(\d+)\s*months?", text, re.IGNORECASE)
    if months_match:
        return int(months_match.group(1)) * 30
    weeks_match = re.match(r"(\d+)\s*weeks?", text, re.IGNORECASE)
    if weeks_match:
        return int(weeks_match.group(1)) * 7
    days_match = re.match(r"(\d+)\s*days?", text, re.IGNORECASE)
    if days_match:
        return int(days_match.group(1))
    cleaned = re.sub(r"[^0-9]", "", text)
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None


def truncate(value: Optional[str], max_len: int = 255) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s[:max_len] if len(s) > max_len else s
