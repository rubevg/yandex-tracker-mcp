import re

MINUTES_PER_HOUR = 60
MINUTES_PER_WORKDAY = 8 * MINUTES_PER_HOUR
MINUTES_PER_WORKWEEK = 5 * MINUTES_PER_WORKDAY

_ISO_DURATION = re.compile(
    r"^P"
    r"(?:(?P<years>\d+)Y)?"
    r"(?:(?P<months>\d+)M)?"
    r"(?:(?P<weeks>\d+)W)?"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?"
    r")?$"
)
_TRACKER_DURATION_PART = re.compile(r"(?P<value>\d+)\s*(?P<unit>[wdhm])", re.IGNORECASE)


def duration_to_minutes(value: str | None) -> int | None:
    """Convert Tracker duration strings to whole working minutes."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.startswith("P"):
        return _iso_duration_to_minutes(normalized)
    return _tracker_duration_to_minutes(normalized)


def _iso_duration_to_minutes(value: str) -> int:
    match = _ISO_DURATION.fullmatch(value)
    if match is None:
        raise ValueError(f"Unsupported ISO 8601 duration: {value}")

    parts = {name: int(raw or 0) for name, raw in match.groupdict().items()}
    if parts["years"] or parts["months"]:
        raise ValueError("Calendar years and months cannot be converted to working minutes")

    return (
        parts["weeks"] * MINUTES_PER_WORKWEEK
        + parts["days"] * MINUTES_PER_WORKDAY
        + parts["hours"] * MINUTES_PER_HOUR
        + parts["minutes"]
        + round(parts["seconds"] / 60)
    )


def _tracker_duration_to_minutes(value: str) -> int:
    matches = list(_TRACKER_DURATION_PART.finditer(value))
    matched_text = "".join(match.group(0) for match in matches).replace(" ", "")
    if not matches or matched_text != value.replace(" ", ""):
        raise ValueError(f"Unsupported Tracker duration: {value}")

    multipliers = {
        "w": MINUTES_PER_WORKWEEK,
        "d": MINUTES_PER_WORKDAY,
        "h": MINUTES_PER_HOUR,
        "m": 1,
    }
    return sum(
        int(match.group("value")) * multipliers[match.group("unit").lower()]
        for match in matches
    )


def format_minutes(minutes: int | None) -> str | None:
    if minutes is None:
        return None
    sign = "-" if minutes < 0 else ""
    remaining = abs(minutes)
    hours, minute_remainder = divmod(remaining, MINUTES_PER_HOUR)
    return f"{sign}{hours}h {minute_remainder}m"
