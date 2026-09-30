from yandex_tracker_mcp.server import mcp


async def test_expected_tools_are_registered() -> None:
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}

    assert names == {
        "add_comment",
        "create_issue",
        "execute_transition",
        "get_issue",
        "list_comments",
        "list_queues",
        "list_transitions",
        "search_issues",
        "update_issue",
    }
