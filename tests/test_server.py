from yandex_tracker_mcp.server import mcp


async def test_expected_tools_are_registered() -> None:
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}

    assert names == {
        "add_checklist_item",
        "add_comment",
        "add_worklog",
        "create_issue",
        "delete_checklist_item",
        "delete_worklog",
        "execute_transition",
        "get_checklist",
        "get_checklist_report",
        "get_current_user",
        "get_global_fields",
        "get_issue",
        "get_issue_types",
        "get_issue_time_report",
        "get_priorities",
        "get_queue_fields",
        "get_resolutions",
        "get_statuses",
        "get_time_report",
        "get_user",
        "list_comments",
        "list_queues",
        "list_transitions",
        "list_users",
        "list_worklogs",
        "search_issues",
        "search_users",
        "update_checklist_item",
        "update_issue",
        "update_worklog",
    }
