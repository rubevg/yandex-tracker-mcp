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
