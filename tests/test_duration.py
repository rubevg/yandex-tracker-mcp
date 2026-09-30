import pytest

from yandex_tracker_mcp.duration import duration_to_minutes, format_minutes
from yandex_tracker_mcp.toolsets.worklogs import _normalize_start, _validate_worklog_duration


@pytest.mark.parametrize(
    ("value", "minutes"),
    [
        ("PT1H30M", 90),
        ("P1W", 2400),
        ("P2DT15M", 975),
        ("1d", 480),
        ("2h 30m", 150),
        ("1w 1d 1h", 2940),
    ],
)
def test_duration_to_working_minutes(value: str, minutes: int) -> None:
    assert duration_to_minutes(value) == minutes


def test_calendar_month_is_rejected() -> None:
    with pytest.raises(ValueError, match="Calendar years and months"):
        duration_to_minutes("P1M")


def test_format_minutes() -> None:
    assert format_minutes(90) == "1h 30m"
    assert format_minutes(-30) == "-0h 30m"
    assert format_minutes(None) is None


def test_worklog_duration_requires_positive_iso_value() -> None:
    assert _validate_worklog_duration("pt1h30m") == "PT1H30M"
    with pytest.raises(ValueError, match="ISO 8601"):
        _validate_worklog_duration("90m")
    with pytest.raises(ValueError, match="greater than zero"):
        _validate_worklog_duration("PT0M")


def test_worklog_start_is_normalized_for_tracker() -> None:
    assert _normalize_start("2026-09-30T10:00:00+03:00") == "2026-09-30T10:00:00.000+0300"
    assert _normalize_start("2026-09-30T10:00:00") == "2026-09-30T10:00:00.000+0000"
