from mcp.server.fastmcp import FastMCP

from .checklists import register_checklist_tools
from .issues import register_issue_tools
from .metadata import register_metadata_tools
from .worklogs import register_worklog_tools


def register_tools(mcp: FastMCP) -> None:
    register_issue_tools(mcp)
    register_metadata_tools(mcp)
    register_checklist_tools(mcp)
    register_worklog_tools(mcp)
