from datetime import UTC, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..analytics import build_issue_time_report, build_time_report
from ..client import TrackerClient
from ..config import get_settings
from ..duration import duration_to_minutes

JsonObject = dict[str, Any]


def _validate_worklog_duration(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized.startswith("P"):
        raise ValueError("duration must use ISO 8601, for example PT1H30M")
    minutes = duration_to_minutes(normalized)
    if minutes is None or minutes <= 0:
        raise ValueError("duration must be greater than zero")
    return normalized


def _normalize_start(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("start must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    timestamp = parsed.strftime("%Y-%m-%dT%H:%M:%S")
    milliseconds = parsed.microsecond // 1000
    return f"{timestamp}.{milliseconds:03d}{parsed.strftime('%z')}"


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
            "Списать время на задачу. Изменяет данные в Трекере; покажите длительность, "
            "дату начала и комментарий пользователю перед вызовом."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )
    async def add_worklog(
        issue_id: str,
        duration: str,
        comment: str | None = None,
        start: str | None = None,
    ) -> JsonObject:
        normalized_duration = _validate_worklog_duration(duration)
        normalized_start = _normalize_start(start) if start is not None else None
        async with TrackerClient(get_settings()) as client:
            return await client.add_worklog(
                issue_id,
                duration=normalized_duration,
                comment=comment,
                start=normalized_start,
            )

    @mcp.tool(
        description=(
            "Изменить запись трудозатрат. Изменяет данные в Трекере; "
            "покажите новые значения пользователю перед вызовом."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )
    async def update_worklog(
        issue_id: str,
        worklog_id: str,
        duration: str | None = None,
        comment: str | None = None,
        start: str | None = None,
    ) -> JsonObject:
        fields: JsonObject = {}
        if duration is not None:
            fields["duration"] = _validate_worklog_duration(duration)
        if comment is not None:
            fields["comment"] = comment
        if start is not None:
            fields["start"] = _normalize_start(start)
        if not fields:
            raise ValueError("provide at least one worklog change")
        async with TrackerClient(get_settings()) as client:
            return await client.update_worklog(issue_id, worklog_id, fields)

    @mcp.tool(
        description=(
            "Удалить запись трудозатрат. Необратимо изменяет данные; "
            "подтвердите задачу и идентификатор записи с пользователем."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )
    async def delete_worklog(issue_id: str, worklog_id: str) -> JsonObject:
        async with TrackerClient(get_settings()) as client:
            await client.delete_worklog(issue_id, worklog_id)
        return {"deleted": True, "issue_id": issue_id, "worklog_id": worklog_id}

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
