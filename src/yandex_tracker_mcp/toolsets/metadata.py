from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..client import TrackerClient
from ..config import get_settings

JsonObject = dict[str, Any]
READ_ONLY = ToolAnnotations(readOnlyHint=True)


def _user_search_text(user: JsonObject) -> list[str]:
    values = [
        user.get("login"),
        user.get("email"),
        user.get("display"),
        user.get("firstName"),
        user.get("lastName"),
    ]
    return [str(value).strip().lower() for value in values if value not in (None, "")]


def register_metadata_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        description="Получить пользователя, которому принадлежит текущий токен Трекера.",
        annotations=READ_ONLY,
    )
    async def get_current_user() -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            return await client.get_current_user()

    @mcp.tool(
        description="Получить пользователя организации по логину или UID.",
        annotations=READ_ONLY,
    )
    async def get_user(user_id: str) -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            return await client.get_user(user_id)

    @mcp.tool(
        description="Получить страницу пользователей организации.",
        annotations=READ_ONLY,
    )
    async def list_users(page: int = 1, per_page: int = 50) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.list_users(page=page, per_page=per_page)

    @mcp.tool(
        description=(
            "Найти пользователей по логину, email, отображаемому имени или фамилии. "
            "Просматривает не более 1000 пользователей."
        ),
        annotations=READ_ONLY,
    )
    async def search_users(query: str, limit: int = 10) -> list[JsonObject]:
        needle = query.strip().lower()
        if not needle:
            raise ValueError("query must not be empty")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")

        matches: list[tuple[int, JsonObject]] = []
        settings = get_settings()
        per_page = min(100, settings.max_response_items)
        max_pages = max(1, 1000 // per_page)
        async with TrackerClient(settings) as client:
            for page in range(1, max_pages + 1):
                users = await client.list_users(page=page, per_page=per_page)
                for user in users:
                    values = _user_search_text(user)
                    if needle in values:
                        return [user]
                    score = 2 if any(value.startswith(needle) for value in values) else 1
                    if any(needle in value for value in values):
                        matches.append((score, user))
                if len(users) < per_page:
                    break

        matches.sort(
            key=lambda item: (
                -item[0],
                str(item[1].get("display") or item[1].get("login") or ""),
            )
        )
        return [user for _, user in matches[:limit]]

    @mcp.tool(
        description="Получить все глобальные поля задач вместе со схемами и типами.",
        annotations=READ_ONLY,
    )
    async def get_global_fields() -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_global_fields()

    @mcp.tool(
        description=(
            "Получить поля очереди. При include_local_fields=true также возвращает "
            "локальные поля этой очереди."
        ),
        annotations=READ_ONLY,
    )
    async def get_queue_fields(
        queue_id: str,
        include_local_fields: bool = True,
    ) -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            fields = await client.get_queue_fields(queue_id)
            local_fields = (
                await client.get_queue_local_fields(queue_id) if include_local_fields else []
            )
        return {"fields": fields, "local_fields": local_fields}

    @mcp.tool(
        description="Получить статусы задач, настроенные в организации.",
        annotations=READ_ONLY,
    )
    async def get_statuses() -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_statuses()

    @mcp.tool(
        description="Получить допустимые типы задач и их ключи.",
        annotations=READ_ONLY,
    )
    async def get_issue_types() -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_issue_types()

    @mcp.tool(
        description="Получить уровни приоритета и ключи для создания или изменения задач.",
        annotations=READ_ONLY,
    )
    async def get_priorities() -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_priorities()

    @mcp.tool(
        description="Получить доступные резолюции для закрытия задач.",
        annotations=READ_ONLY,
    )
    async def get_resolutions() -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_resolutions()
