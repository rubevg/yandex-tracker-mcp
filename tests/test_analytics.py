from typing import Any

import pytest

from yandex_tracker_mcp.analytics import (
    build_checklist_report,
    build_issue_time_report,
    build_time_report,
)


class FakeTrackerClient:
    def __init__(
        self,
        issues: list[dict[str, Any]],
        worklogs: dict[str, list[dict[str, Any]]],
    ) -> None:
        self.issues = issues
        self.worklogs = worklogs

    async def get_issue(self, issue_id: str) -> dict[str, Any]:
        return next(issue for issue in self.issues if issue["key"] == issue_id)

    async def get_issue_worklogs(
        self,
        issue_id: str,
        *,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        return self.worklogs.get(issue_id, [])[:limit]

    async def search_issues(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 50,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        del query, fields
        start = (page - 1) * per_page
        return self.issues[start : start + per_page]


@pytest.fixture
def fake_client() -> FakeTrackerClient:
    issues = [
        {
            "key": "TEST-1",
            "summary": "First",
            "queue": {"key": "TEST"},
            "originalEstimation": "8h",
            "estimation": "10h",
            "spent": "PT3H",
        },
        {
            "key": "TEST-2",
            "summary": "Second",
            "queue": {"key": "TEST"},
            "estimation": "2h",
        },
    ]
    worklogs = {
        "TEST-1": [
            {
                "id": "1",
                "duration": "PT1H30M",
                "start": "2026-09-01T10:00:00.000+0300",
                "createdBy": {"login": "alice"},
            },
            {
                "id": "2",
                "duration": "PT1H30M",
                "start": "2026-09-02T10:00:00.000+0300",
                "createdBy": {"login": "bob"},
            },
        ],
        "TEST-2": [
            {
                "id": "3",
                "duration": "PT2H",
                "start": "2026-09-02T12:00:00.000+0300",
                "createdBy": {"login": "alice"},
            }
        ],
    }
    return FakeTrackerClient(issues, worklogs)


async def test_issue_time_report_filters_period(fake_client: FakeTrackerClient) -> None:
    report = await build_issue_time_report(
        fake_client,  # type: ignore[arg-type]
        "TEST-1",
        date_from="2026-09-02",
        date_to="2026-09-02",
    )

    assert report["actual"]["total_minutes"] == 90
    assert report["actual"]["by_user"] == [
        {"name": "bob", "minutes": 90, "display": "1h 30m"}
    ]
    assert report["estimate"]["current_minutes"] == 600
    assert report["variance_minutes"] == -510


async def test_team_time_report_groups_all_dimensions(fake_client: FakeTrackerClient) -> None:
    report = await build_time_report(
        fake_client,  # type: ignore[arg-type]
        'Queue: "TEST"',
        max_issues=2,
        concurrency=2,
    )

    assert report["summary"]["total_minutes"] == 300
    assert report["summary"]["entry_count"] == 3
    assert report["summary"]["by_user"][0] == {
        "name": "alice",
        "minutes": 210,
        "display": "3h 30m",
    }
    assert report["current_estimate_minutes"] == 720
    assert report["utilization_percent"] == pytest.approx(41.67)


async def test_report_rejects_inverted_period(fake_client: FakeTrackerClient) -> None:
    with pytest.raises(ValueError, match="date_from"):
        await build_time_report(
            fake_client,  # type: ignore[arg-type]
            "Queue: TEST",
            date_from="2026-09-03",
            date_to="2026-09-01",
        )


def test_checklist_report_tracks_progress_overdue_and_assignees() -> None:
    checklist = [
        {
            "id": "1",
            "text": "Done",
            "checked": True,
            "assignee": {"login": "alice"},
        },
        {
            "id": "2",
            "text": "Late",
            "checked": False,
            "assignee": {"login": "alice"},
            "deadline": {"date": "2026-09-01T00:00:00.000+0000"},
        },
        {"id": "3", "text": "Open", "checked": False},
    ]

    report = build_checklist_report("TEST-1", checklist, as_of="2026-09-30")

    assert report["progress_percent"] == pytest.approx(33.33)
    assert report["overdue_count"] == 1
    assert report["overdue_items"][0]["id"] == "2"
    assert report["by_assignee"] == [
        {
            "assignee": "alice",
            "total": 2,
            "completed": 1,
            "open": 1,
            "overdue": 1,
        },
        {
            "assignee": "unassigned",
            "total": 1,
            "completed": 0,
            "open": 1,
            "overdue": 0,
        },
    ]


def test_empty_checklist_is_complete() -> None:
    report = build_checklist_report("TEST-1", [], as_of="2026-09-30")

    assert report["progress_percent"] == 100.0
    assert report["total"] == 0
