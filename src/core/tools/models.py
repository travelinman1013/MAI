"""
Pydantic models for MAI Tools.

This module defines data structures related to tool metadata and functionality.
"""

from pydantic import BaseModel, Field


class ToolMetadata(BaseModel):
    """
    Metadata for an AI agent tool.

    Attributes:
        name: The unique name of the tool (snake_case recommended).
        description: A brief, clear description of what the tool does.
        category: The category the tool belongs to (e.g., "math", "web_search", "file_io").
        parameters: A JSON schema representation of the tool's input parameters.
                    Derived automatically from the tool function's signature if not provided.
        returns: A JSON schema representation of the tool's return type.
        version: The version of the tool. Defaults to "1.0.0".
        enabled: Whether the tool is currently enabled for use. Defaults to True.
    """

    name: str = Field(..., description="The unique name of the tool.")
    description: str = Field(..., description="A brief, clear description of what the tool does.")
    category: str = Field("general", description="The category the tool belongs to.")
    parameters: dict = Field(default_factory=dict, description="JSON schema for tool's input parameters.")
    returns: dict = Field(default_factory=dict, description="JSON schema for tool's return type.")
    version: str = Field("1.0.0", description="The version of the tool.")
    enabled: bool = Field(True, description="Whether the tool is currently enabled for use.")
