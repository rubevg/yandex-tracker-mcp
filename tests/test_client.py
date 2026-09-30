import pytest
from aioresponses import aioresponses

from yandex_tracker_mcp.client import TrackerAPIError, TrackerClient
from yandex_tracker_mcp.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(token="oauth-token", org_id="org-id")


async def test_get_issue(settings: Settings) -> None:
    url = "https://api.tracker.yandex.net/v3/issues/TEST-1"
    with aioresponses() as mocked:
        mocked.get(url, payload={"key": "TEST-1", "summary": "Example"})

        async with TrackerClient(settings) as client:
            issue = await client.get_issue("TEST-1")

    assert issue["key"] == "TEST-1"
    request = next(iter(mocked.requests.values()))[0]
    assert request.kwargs["headers"]["Authorization"] == "OAuth oauth-token"
    assert request.kwargs["headers"]["X-Org-ID"] == "org-id"


async def test_api_error_is_sanitized(settings: Settings) -> None:
    url = "https://api.tracker.yandex.net/v3/issues/MISSING-1"
    with aioresponses() as mocked:
        mocked.get(url, status=404, payload={"message": "Issue not found"})

        async with TrackerClient(settings) as client:
            with pytest.raises(TrackerAPIError, match="Issue not found") as error:
                await client.get_issue("MISSING-1")

    assert error.value.status == 404
    assert "oauth-token" not in str(error.value)


async def test_client_requires_context_manager(settings: Settings) -> None:
    client = TrackerClient(settings)

    with pytest.raises(RuntimeError, match="async context manager"):
        await client.get_issue("TEST-1")


async def test_checklist_item_lifecycle(settings: Settings) -> None:
    base_url = "https://api.tracker.yandex.net/v3/issues/TEST-1/checklistItems"
    first = [{"id": "item-1", "text": "Review", "checked": False}]
    updated = [{"id": "item-1", "text": "Review", "checked": True}]

    with aioresponses() as mocked:
        mocked.get(base_url, payload=first)
        mocked.post(base_url, payload={"checklistItems": first})
        mocked.patch(f"{base_url}/item-1", payload={"checklistItems": updated})
        mocked.delete(f"{base_url}/item-1", payload={"checklistItems": []})

        async with TrackerClient(settings) as client:
            assert await client.get_checklist("TEST-1") == first
            assert (
                await client.add_checklist_item("TEST-1", text="Review", checked=False) == first
            )
            assert (
                await client.update_checklist_item("TEST-1", "item-1", {"checked": True})
                == updated
            )
            assert await client.delete_checklist_item("TEST-1", "item-1") == []


async def test_worklog_relative_pagination(settings: Settings) -> None:
    settings.max_response_items = 2
    base_url = "https://api.tracker.yandex.net/v3/issues/TEST-1/worklog"
    first_page = [
        {"id": "1", "duration": "PT1H"},
        {"id": "2", "duration": "PT30M"},
    ]
    second_page = [{"id": "3", "duration": "PT15M"}]

    with aioresponses() as mocked:
        mocked.get(f"{base_url}?perPage=2", payload=first_page)
        mocked.get(f"{base_url}?perPage=1&id=2", payload=second_page)

        async with TrackerClient(settings) as client:
            worklogs = await client.get_issue_worklogs("TEST-1", limit=3)

    assert [entry["id"] for entry in worklogs] == ["1", "2", "3"]


async def test_worklog_limit_is_bounded(settings: Settings) -> None:
    async with TrackerClient(settings) as client:
        with pytest.raises(ValueError, match="between 1 and 500"):
            await client.get_issue_worklogs("TEST-1", limit=501)
