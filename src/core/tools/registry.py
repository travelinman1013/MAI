"""
Tool Registry for MAI Framework.

This module provides a thread-safe, global registry for managing AI agent tools.
"""

import threading
from typing import Callable, Any, Optional

from src.core.tools.models import ToolMetadata


class ToolRegistry:
    """
    Thread-safe, global registry for AI agent tools.

    Ensures that tools can be registered and retrieved consistently
    across different parts of the application, including concurrent contexts.
    """

    _instance: Optional["ToolRegistry"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "ToolRegistry":
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tools: dict[str, tuple[Callable[..., Any], ToolMetadata]] = {}
                    cls._instance._categories: dict[str, list[str]] = {}
        return cls._instance

    def register(self, func: Callable[..., Any], metadata: ToolMetadata) -> None:
        """
        Registers a tool function and its metadata.

        Args:
            func: The callable function representing the tool.
            metadata: The ToolMetadata instance for the tool.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        with self._lock:
            if metadata.name in self._tools:
                raise ValueError(f"Tool with name '{metadata.name}' already registered.")
            self._tools[metadata.name] = (func, metadata)

            if metadata.category not in self._categories:
                self._categories[metadata.category] = []
            self._categories[metadata.category].append(metadata.name)

    def get_tool(self, name: str) -> Optional[tuple[Callable[..., Any], ToolMetadata]]:
        """
        Retrieves a registered tool by its name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            A tuple containing the callable function and its metadata, or None if not found.
        """
        with self._lock:
            return self._tools.get(name)

    def list_tools_by_category(self, category: str) -> list[tuple[Callable[..., Any], ToolMetadata]]:
        """
        Lists all tools belonging to a specific category.

        Args:
            category: The category name.

        Returns:
            A list of tuples, each containing a callable function and its metadata,
            for all tools in the specified category. Returns an empty list if the
            category does not exist or has no tools.
        """
        with self._lock:
            tool_names = self._categories.get(category, [])
            return [self._tools[name] for name in tool_names if name in self._tools]

    def list_all_tools(self) -> list[tuple[Callable[..., Any], ToolMetadata]]:
        """
        Lists all registered tools.

        Returns:
            A list of tuples, each containing a callable function and its metadata.
        """
        with self._lock:
            return list(self._tools.values())

    def unregister_tool(self, name: str) -> None:
        """
        Unregisters a tool by its name.

        Args:
            name: The name of the tool to unregister.
        """
        with self._lock:
            if name in self._tools:
                func, metadata = self._tools.pop(name)
                if metadata.category in self._categories and name in self._categories[metadata.category]:
                    self._categories[metadata.category].remove(name)
                    if not self._categories[metadata.category]:
                        del self._categories[metadata.category]
            
    def clear(self) -> None:
        """Clears all registered tools. Useful for testing."""
        with self._lock:
            self._tools.clear()
            self._categories.clear()

# Global instance of the ToolRegistry
tool_registry = ToolRegistry()
