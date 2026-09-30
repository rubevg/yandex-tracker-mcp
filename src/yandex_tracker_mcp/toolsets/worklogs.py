from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..analytics import build_issue_time_report, build_time_report
from ..client import TrackerClient
from ..config import get_settings

JsonObject = dict[str, Any]


def register_worklog_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        description=(
            "Получить записи трудозатрат задачи. Автоматически загружает страницы, "
            "но возвращает не более 500 записей."
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_worklogs(issue_id: str, limit: int = 500) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_issue_worklogs(issue_id, limit=limit)

    @mcp.tool(
        description=(
            "Проанализировать трудозатраты одной задачи: план, факт, отклонение "
            "и разбивка по сотрудникам и дням. Даты задаются как YYYY-MM-DD."
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_issue_time_report(
        issue_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            return await build_issue_time_report(
                client,
                issue_id,
                date_from=date_from,
                date_to=date_to,
            )

    @mcp.tool(
        description=(
            "Построить сводный отчёт по задачам из запроса Tracker: итоги и разбивка "
            "по сотрудникам, задачам, очередям и дням. Даты задаются как YYYY-MM-DD."
        ),
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_time_report(
        query: str,
        date_from: str | None = None,
        date_to: str | None = None,
        max_issues: int = 50,
        concurrency: int = 5,
    ) -> JsonObject:
        if not query.strip():
            raise ValueError("query must not be empty")
        async with TrackerClient(get_settings()) as client:
            return await build_time_report(
                client,
                query,
                date_from=date_from,
                date_to=date_to,
                max_issues=max_issues,
                concurrency=concurrency,
            )
