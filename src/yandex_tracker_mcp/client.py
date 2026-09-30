from collections.abc import Mapping
from typing import Any

import aiohttp

from .config import Settings

JsonObject = dict[str, Any]


class TrackerAPIError(RuntimeError):
    """A sanitized error returned by Yandex Tracker."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"Yandex Tracker API returned HTTP {status}: {message}")
        self.status = status


class TrackerClient:
    def __init__(
        self,
        settings: Settings,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self.settings = settings
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self) -> "TrackerClient":
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.settings.request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
        json: JsonObject | None = None,
    ) -> Any:
        if self._session is None:
            raise RuntimeError("TrackerClient must be used as an async context manager")

        url = f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}"
        async with self._session.request(
            method,
            url,
            headers=self.settings.headers,
            params=params,
            json=json,
        ) as response:
            if response.status >= 400:
                try:
                    payload = await response.json()
                    message = payload.get("message") or payload.get("errorMessages") or str(payload)
                except (aiohttp.ContentTypeError, ValueError):
                    message = (await response.text())[:500] or response.reason
                raise TrackerAPIError(response.status, str(message))

            if response.status == 204:
                return None
            return await response.json()

    async def get_issue(self, issue_id: str, fields: list[str] | None = None) -> JsonObject:
        params = {"expand": ",".join(fields)} if fields else None
        result = await self._request("GET", f"issues/{issue_id}", params=params)
        return self._expect_object(result)

    async def search_issues(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 50,
        fields: list[str] | None = None,
    ) -> list[JsonObject]:
        body: JsonObject = {"query": query}
        params: dict[str, str | int] = {
            "page": page,
            "perPage": min(per_page, self.settings.max_response_items),
        }
        if fields:
            params["fields"] = ",".join(fields)
        result = await self._request(
            "POST",
            "issues/_search",
            params=params,
            json=body,
        )
        return self._expect_list(result)

    async def create_issue(self, fields: JsonObject) -> JsonObject:
        result = await self._request("POST", "issues", json=fields)
        return self._expect_object(result)

    async def update_issue(self, issue_id: str, fields: JsonObject) -> JsonObject:
        result = await self._request("PATCH", f"issues/{issue_id}", json=fields)
        return self._expect_object(result)

    async def list_comments(self, issue_id: str) -> list[JsonObject]:
        result = await self._request(
            "GET",
            f"issues/{issue_id}/comments",
            params={"perPage": self.settings.max_response_items},
        )
        return self._expect_list(result)

    async def add_comment(
        self,
        issue_id: str,
        text: str,
        *,
        summonees: list[str] | None = None,
    ) -> JsonObject:
        body: JsonObject = {"text": text}
        if summonees is not None:
            body["summonees"] = summonees
        result = await self._request(
            "POST",
            f"issues/{issue_id}/comments",
            json=body,
        )
        return self._expect_object(result)

    async def list_queues(self, *, page: int = 1, per_page: int = 50) -> list[JsonObject]:
        result = await self._request(
            "GET",
            "queues",
            params={"page": page, "perPage": min(per_page, self.settings.max_response_items)},
        )
        return self._expect_list(result)

    async def list_transitions(self, issue_id: str) -> list[JsonObject]:
        result = await self._request("GET", f"issues/{issue_id}/transitions")
        return self._expect_list(result)

    async def execute_transition(
        self,
        issue_id: str,
        transition_id: str,
        fields: JsonObject | None = None,
    ) -> JsonObject:
        result = await self._request(
            "POST",
            f"issues/{issue_id}/transitions/{transition_id}/_execute",
            json=fields or {},
        )
        return self._expect_object(result)

    async def get_checklist(self, issue_id: str) -> list[JsonObject]:
        result = await self._request("GET", f"issues/{issue_id}/checklistItems")
        return self._expect_list(result)

    async def add_checklist_item(
        self,
        issue_id: str,
        *,
        text: str,
        checked: bool = False,
        assignee: str | None = None,
        deadline: JsonObject | None = None,
    ) -> list[JsonObject]:
        body: JsonObject = {"text": text, "checked": checked}
        if assignee is not None:
            body["assignee"] = assignee
        if deadline is not None:
            body["deadline"] = deadline
        result = await self._request(
            "POST",
            f"issues/{issue_id}/checklistItems",
            json=body,
        )
        return self._checklist_from_issue(result)

    async def update_checklist_item(
        self,
        issue_id: str,
        checklist_item_id: str,
        fields: JsonObject,
    ) -> list[JsonObject]:
        if not fields:
            raise ValueError("checklist item update must not be empty")
        result = await self._request(
            "PATCH",
            f"issues/{issue_id}/checklistItems/{checklist_item_id}",
            json=fields,
        )
        return self._checklist_from_issue(result)

    async def delete_checklist_item(
        self,
        issue_id: str,
        checklist_item_id: str,
    ) -> list[JsonObject]:
        result = await self._request(
            "DELETE",
            f"issues/{issue_id}/checklistItems/{checklist_item_id}",
        )
        return self._checklist_from_issue(result)

    async def get_issue_worklogs(
        self,
        issue_id: str,
        *,
        limit: int = 500,
    ) -> list[JsonObject]:
        if not 1 <= limit <= 500:
            raise ValueError("worklog limit must be between 1 and 500")
        effective_limit = limit
        worklogs: list[JsonObject] = []
        cursor: str | None = None

        while len(worklogs) < effective_limit:
            per_page = min(self.settings.max_response_items, effective_limit - len(worklogs))
            params: dict[str, str | int] = {"perPage": per_page}
            if cursor is not None:
                params["id"] = cursor

            result = await self._request(
                "GET",
                f"issues/{issue_id}/worklog",
                params=params,
            )
            page = self._expect_list(result)
            worklogs.extend(page)
            if len(page) < per_page:
                break

            next_cursor = str(page[-1].get("id", ""))
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        return worklogs[:effective_limit]

    @classmethod
    def _checklist_from_issue(cls, value: Any) -> list[JsonObject]:
        issue = cls._expect_object(value)
        checklist = issue.get("checklistItems", [])
        return cls._expect_list(checklist)

    @staticmethod
    def _expect_object(value: Any) -> JsonObject:
        if not isinstance(value, dict):
            raise TrackerAPIError(502, "unexpected non-object response")
        return value

    @staticmethod
    def _expect_list(value: Any) -> list[JsonObject]:
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise TrackerAPIError(502, "unexpected non-list response")
        return value
