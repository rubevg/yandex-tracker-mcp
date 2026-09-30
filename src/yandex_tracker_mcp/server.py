from mcp.server.fastmcp import FastMCP

from .tools import register_tools

mcp = FastMCP(
    "Yandex Tracker",
    instructions=(
        "Use read tools freely. Before create_issue, update_issue, add_comment, or "
        "execute_transition, show the proposed change and obtain user confirmation."
    ),
)
register_tools(mcp)


def run() -> None:
    mcp.run(transport="stdio")
