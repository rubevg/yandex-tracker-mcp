from mcp.server.fastmcp import FastMCP

from .toolsets import register_tools

mcp = FastMCP(
    "Yandex Tracker",
    instructions=(
        "Use read and reporting tools freely. Before any tool that creates, updates, "
        "deletes, comments on, or transitions Tracker data, show the proposed change "
        "and obtain user confirmation."
    ),
)
register_tools(mcp)


def run() -> None:
    mcp.run(transport="stdio")
