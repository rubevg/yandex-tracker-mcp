from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..client import TrackerClient
from ..config import get_settings

JsonObject = dict[str, Any]


def _deadline(date: str, deadline_type: str) -> JsonObject:
    if deadline_type not in {"date", "datetime"}:
        raise ValueError("deadline_type must be 'date' or 'datetime'")
    return {"date": date, "deadlineType": deadline_type}


def register_checklist_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        description="Получить пункты чек-листа задачи вместе с их идентификаторами.",
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_checklist(issue_id: str) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.get_checklist(issue_id)

    @mcp.tool(
        description=(
            "Добавить пункт чек-листа. Изменяет задачу; покажите текст, исполнителя "
            "и срок пользователю перед вызовом."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
    )
    async def add_checklist_item(
        issue_id: str,
        text: str,
        checked: bool = False,
        assignee: str | None = None,
        deadline: str | None = None,
        deadline_type: str = "date",
    ) -> list[JsonObject]:
        if not text.strip():
            raise ValueError("text must not be empty")
        deadline_body = _deadline(deadline, deadline_type) if deadline is not None else None
        async with TrackerClient(get_settings()) as client:
            return await client.add_checklist_item(
                issue_id,
                text=text,
                checked=checked,
                assignee=assignee,
                deadline=deadline_body,
            )

    @mcp.tool(
        description=(
            "Изменить один пункт чек-листа: текст, выполнение, исполнителя или срок. "
            "Изменяет задачу; покажите изменения пользователю перед вызовом."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )
    async def update_checklist_item(
        issue_id: str,
        checklist_item_id: str,
        text: str | None = None,
        checked: bool | None = None,
        assignee: str | None = None,
        deadline: str | None = None,
        deadline_type: str = "date",
        clear_assignee: bool = False,
        clear_deadline: bool = False,
    ) -> list[JsonObject]:
        if assignee is not None and clear_assignee:
            raise ValueError("assignee and clear_assignee cannot be used together")
        if deadline is not None and clear_deadline:
            raise ValueError("deadline and clear_deadline cannot be used together")

        fields: JsonObject = {}
        if text is not None:
            if not text.strip():
                raise ValueError("text must not be empty")
            fields["text"] = text
        if checked is not None:
            fields["checked"] = checked
        if assignee is not None:
            fields["assignee"] = assignee
        elif clear_assignee:
            fields["assignee"] = {}
        if deadline is not None:
            fields["deadline"] = _deadline(deadline, deadline_type)
        elif clear_deadline:
            fields["deadline"] = {}
        if not fields:
            raise ValueError("provide at least one checklist item change")

        async with TrackerClient(get_settings()) as client:
            return await client.update_checklist_item(
                issue_id,
                checklist_item_id,
                fields,
            )

    @mcp.tool(
        description=(
            "Удалить один пункт чек-листа. Необратимо изменяет задачу; "
            "подтвердите идентификатор пункта с пользователем."
        ),
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
    )
    async def delete_checklist_item(
        issue_id: str,
        checklist_item_id: str,
    ) -> list[JsonObject]:
        async with TrackerClient(get_settings()) as client:
            return await client.delete_checklist_item(issue_id, checklist_item_id)
