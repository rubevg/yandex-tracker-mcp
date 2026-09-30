import pytest
from pydantic import ValidationError

from yandex_tracker_mcp.config import Settings


def test_oauth_and_yandex_360_headers() -> None:
    settings = Settings(token="secret", org_id="42")

    assert settings.headers == {
        "Authorization": "OAuth secret",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Org-ID": "42",
    }


def test_iam_and_cloud_headers() -> None:
    settings = Settings(iam_token="iam-secret", cloud_org_id="cloud")

    assert settings.headers["Authorization"] == "Bearer iam-secret"
    assert settings.headers["X-Cloud-Org-ID"] == "cloud"


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"token": "one", "iam_token": "two", "org_id": "42"},
        {"token": "one"},
        {"token": "one", "org_id": "42", "cloud_org_id": "cloud"},
    ],
)
def test_requires_exactly_one_auth_and_org(values: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        Settings(**values)
