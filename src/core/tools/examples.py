"""
Example Tools for MAI Framework.

This module provides example tool implementations to demonstrate
how to create and register tools that agents can use.
"""

from datetime import datetime
from typing import Optional
import random

from src.core.tools.base import tool


@tool(
    name="get_current_time",
    description="Get the current date and time in ISO format",
    category="utility"
)
def get_current_time() -> str:
    """
    Returns the current date and time in ISO 8601 format.

    Returns:
        Current datetime as ISO formatted string
    """
    return datetime.utcnow().isoformat() + "Z"


@tool(
    name="calculate",
    description="Perform basic arithmetic calculations (add, subtract, multiply, divide)",
    category="math"
)
def calculate(operation: str, a: float, b: float) -> float:
    """
    Perform basic arithmetic operations.

    Args:
        operation: The operation to perform ('add', 'subtract', 'multiply', 'divide')
        a: First number
        b: Second number

    Returns:
        Result of the calculation

    Raises:
        ValueError: If operation is not supported or division by zero
    """
    operation = operation.lower()

    if operation in ("add", "+"):
        return a + b
    elif operation in ("subtract", "-"):
        return a - b
    elif operation in ("multiply", "*"):
        return a * b
    elif operation in ("divide", "/"):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unsupported operation: {operation}. Use add, subtract, multiply, or divide.")


@tool(
    name="generate_random_number",
    description="Generate a random number within a specified range",
    category="utility"
)
def generate_random_number(min_value: int = 1, max_value: int = 100) -> int:
    """
    Generate a random integer within the specified range (inclusive).

    Args:
        min_value: Minimum value (default: 1)
        max_value: Maximum value (default: 100)

    Returns:
        Random integer between min_value and max_value (inclusive)

    Raises:
        ValueError: If min_value > max_value
    """
    if min_value > max_value:
        raise ValueError(f"min_value ({min_value}) cannot be greater than max_value ({max_value})")

    return random.randint(min_value, max_value)


@tool(
    name="string_length",
    description="Get the length of a string",
    category="utility"
)
def string_length(text: str) -> int:
    """
    Returns the length of the provided string.

    Args:
        text: The string to measure

    Returns:
        Length of the string
    """
    return len(text)


@tool(
    name="reverse_string",
    description="Reverse a string",
    category="utility"
)
def reverse_string(text: str) -> str:
    """
    Reverses the provided string.

    Args:
        text: The string to reverse

    Returns:
        Reversed string
    """
    return text[::-1]


@tool(
    name="count_words",
    description="Count the number of words in a text",
    category="utility"
)
def count_words(text: str) -> int:
    """
    Counts the number of words in the provided text.
    Words are separated by whitespace.

    Args:
        text: The text to analyze

    Returns:
        Number of words in the text
    """
    return len(text.split())


@tool(
    name="fahrenheit_to_celsius",
    description="Convert temperature from Fahrenheit to Celsius",
    category="conversion"
)
def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    Convert temperature from Fahrenheit to Celsius.

    Args:
        fahrenheit: Temperature in Fahrenheit

    Returns:
        Temperature in Celsius
    """
    return (fahrenheit - 32) * 5 / 9


@tool(
    name="celsius_to_fahrenheit",
    description="Convert temperature from Celsius to Fahrenheit",
    category="conversion"
)
def celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius

    Returns:
        Temperature in Fahrenheit
    """
    return (celsius * 9 / 5) + 32


# Auto-register all tools when this module is imported
# The @tool decorator automatically registers tools with the global registry
