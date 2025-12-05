"""
Tool API Routes.

This module implements the FastAPI endpoints for tool listing and management.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from src.core.tools.registry import tool_registry
from src.core.utils.logging import get_logger_with_context

router = APIRouter()
logger = get_logger_with_context(module="tool_routes")


@router.get(
    "/",
    summary="List all tools",
    description="Get a list of all registered tools with their metadata."
)
async def list_tools(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    List all available tools.

    - **category**: Optional filter by tool category

    Returns list of tools with names, descriptions, and metadata.
    """
    try:
        all_tools = tool_registry.list_all_tools()

        tools_list = []
        for func, metadata in all_tools:
            if category and metadata.category != category:
                continue

            tools_list.append({
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category,
                "parameters": metadata.parameters,
                "version": metadata.version,
                "enabled": metadata.enabled,
            })

        return {
            "success": True,
            "tools": tools_list,
            "count": len(tools_list)
        }

    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "TOOL_LIST_ERROR", "message": str(e)}
        )


@router.get(
    "/categories",
    summary="List tool categories",
    description="Get a list of all tool categories."
)
async def list_categories():
    """
    List all tool categories.

    Returns list of category names with tool counts.
    """
    try:
        all_tools = tool_registry.list_all_tools()

        categories: dict = {}
        for func, metadata in all_tools:
            cat = metadata.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        return {
            "success": True,
            "categories": [
                {"name": cat, "count": count}
                for cat, count in sorted(categories.items())
            ]
        }

    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "CATEGORY_LIST_ERROR", "message": str(e)}
        )


@router.get(
    "/{tool_name}",
    summary="Get tool details",
    description="Get detailed information about a specific tool."
)
async def get_tool(tool_name: str):
    """
    Get details for a specific tool.

    - **tool_name**: Name of the tool to retrieve

    Returns tool metadata and parameter schema.
    """
    try:
        tool_info = tool_registry.get_tool(tool_name)

        if not tool_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error_code": "TOOL_NOT_FOUND", "message": f"Tool '{tool_name}' not found"}
            )

        func, metadata = tool_info

        return {
            "success": True,
            "tool": {
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category,
                "parameters": metadata.parameters,
                "returns": metadata.returns,
                "version": metadata.version,
                "enabled": metadata.enabled,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool '{tool_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "TOOL_GET_ERROR", "message": str(e)}
        )
