from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from TRACKER_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="TRACKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    token: SecretStr | None = None
    iam_token: SecretStr | None = None
    org_id: str | None = None
    cloud_org_id: str | None = None
    base_url: str = "https://api.tracker.yandex.net/v3"
    request_timeout: float = Field(default=30.0, gt=0, le=300)
    max_response_items: int = Field(default=100, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_credentials(self) -> "Settings":
        if (self.token is None) == (self.iam_token is None):
            raise ValueError("Set exactly one of TRACKER_TOKEN or TRACKER_IAM_TOKEN")
        if (self.org_id is None) == (self.cloud_org_id is None):
            raise ValueError("Set exactly one of TRACKER_ORG_ID or TRACKER_CLOUD_ORG_ID")
        return self

    @property
    def headers(self) -> dict[str, str]:
        if self.token is not None:
            authorization = f"OAuth {self.token.get_secret_value()}"
        else:
            assert self.iam_token is not None
            authorization = f"Bearer {self.iam_token.get_secret_value()}"

        if self.org_id is not None:
            organization = {"X-Org-ID": self.org_id}
        else:
            assert self.cloud_org_id is not None
            organization = {"X-Cloud-Org-ID": self.cloud_org_id}
        return {
            "Authorization": authorization,
            "Accept": "application/json",
            "Content-Type": "application/json",
            **organization,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
