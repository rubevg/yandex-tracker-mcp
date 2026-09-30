from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .client import TrackerClient
from .config import get_settings

JsonObject = dict[str, Any]


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        description="Получить задачу Яндекс Трекера по ключу, например TEST-123.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_issue(issue_id: str, fields: list[str] | None = None) -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            return await client.get_issue(issue_id, fields)

    @mcp.tool(
        description="Найти задачи на языке запросов Яндекс Трекера.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def search_issues(
        query: str,
        page: int = 1,
        per_page: int = 50,
        fields: list[str] | None = None,
    ) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.search_issues(
                query,
                page=page,
                per_page=per_page,
                fields=fields,
            )

    @mcp.tool(
        description=(
            "Создать задачу. Изменяет данные в Трекере; перед вызовом подтвердите "
            "название и очередь с пользователем."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )
    async def create_issue(
        summary: str,
        queue: str,
        description: str | None = None,
        issue_type: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        fields: JsonObject | None = None,
    ) -> JsonObject:
        body = dict(fields or {})
        body.update({"summary": summary, "queue": queue})
        optional = {
            "description": description,
            "type": issue_type,
            "priority": priority,
            "assignee": assignee,
        }
        body.update({key: value for key, value in optional.items() if value is not None})
        async with TrackerClient(get_settings()) as client:
            return await client.create_issue(body)

    @mcp.tool(
        description=(
            "Обновить поля существующей задачи. Изменяет данные в Трекере; "
            "покажите изменения пользователю перед вызовом."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )
    async def update_issue(issue_id: str, fields: JsonObject) -> JsonObject:
        if not fields:
            raise ValueError("fields must not be empty")
        async with TrackerClient(get_settings()) as client:
            return await client.update_issue(issue_id, fields)

    @mcp.tool(
        description="Получить комментарии задачи.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_comments(issue_id: str) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.list_comments(issue_id)

    @mcp.tool(
        description=(
            "Добавить комментарий к задаче. Изменяет данные в Трекере; "
            "покажите текст пользователю перед вызовом."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )
    async def add_comment(
        issue_id: str,
        text: str,
        summonees: list[str] | None = None,
    ) -> JsonObject:
        if not text.strip():
            raise ValueError("text must not be empty")
        async with TrackerClient(get_settings()) as client:
            return await client.add_comment(issue_id, text, summonees=summonees)

    @mcp.tool(
        description="Получить доступные очереди Яндекс Трекера.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_queues(page: int = 1, per_page: int = 50) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.list_queues(page=page, per_page=per_page)

    @mcp.tool(
        description="Получить доступные переходы статуса для задачи.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_transitions(issue_id: str) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.list_transitions(issue_id)

    @mcp.tool(
        description=(
            "Выполнить переход статуса задачи. Изменяет данные в Трекере; "
            "подтвердите целевой переход с пользователем."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )
    async def execute_transition(
        issue_id: str,
        transition_id: str,
        fields: JsonObject | None = None,
    ) -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            return await client.execute_transition(issue_id, transition_id, fields)
