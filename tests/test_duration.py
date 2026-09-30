import pytest

from yandex_tracker_mcp.duration import duration_to_minutes, format_minutes


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
