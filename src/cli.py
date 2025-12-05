"""
MAI Framework CLI.

Interactive command-line interface for agent execution, streaming, and management.
"""

import asyncio
import json
import signal
import sys
import uuid
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Initialize console for rich output
console = Console()

# Default API URL
DEFAULT_API_URL = "http://localhost:8000"

# Version
VERSION = "0.1.0"


def get_api_url(api_url: Optional[str] = None) -> str:
    """Get the API URL from parameter, env var, or default."""
    import os
    return api_url or os.environ.get("MAI_API_URL", DEFAULT_API_URL)


def handle_interrupt(signum, frame):
    """Handle Ctrl+C gracefully."""
    console.print("\n[dim]Interrupted. Goodbye![/dim]")
    sys.exit(0)


# Register signal handler
signal.signal(signal.SIGINT, handle_interrupt)


@click.group()
@click.version_option(version=VERSION, prog_name="mai")
def main():
    """MAI Framework CLI - AI Agent Management and Interaction"""
    pass


@main.command()
@click.option("--agent", "-a", default="simple_agent", help="Agent to chat with")
@click.option("--session", "-s", default=None, help="Session ID (generates UUID if not provided)")
@click.option("--stream/--no-stream", default=True, help="Enable streaming responses")
@click.option("--api-url", envvar="MAI_API_URL", default=DEFAULT_API_URL, help="API base URL")
def chat(agent: str, session: Optional[str], stream: bool, api_url: str):
    """Start an interactive chat session with an agent."""
    # Generate session ID if not provided
    session_id = session or str(uuid.uuid4())

    # Display header panel
    header = Text()
    header.append(f"MAI Framework v{VERSION}\n", style="bold blue")
    header.append(f"Agent: ", style="dim")
    header.append(f"{agent}\n", style="cyan")
    header.append(f"Session: ", style="dim")
    header.append(f"{session_id[:8]}...{session_id[-4:]}", style="green")

    console.print(Panel(header, title="[bold]MAI Chat[/bold]", border_style="blue"))
    console.print()
    console.print("[dim]Type /help for commands, /quit to exit[/dim]")
    console.print()

    # Run the async chat loop
    try:
        asyncio.run(_chat_loop(agent, session_id, stream, api_url))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye! Session saved.[/dim]")


async def _chat_loop(agent: str, session_id: str, stream: bool, api_url: str):
    """Main chat loop."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        while True:
            try:
                # Get user input
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

                if not user_input.strip():
                    continue

                # Handle special commands
                if user_input.startswith("/"):
                    command = user_input.lower().strip()

                    if command in ("/quit", "/exit", "/q"):
                        console.print(f"\n[dim]Goodbye! Session: {session_id[:8]}...[/dim]")
                        break

                    elif command == "/help":
                        _show_help()
                        continue

                    elif command == "/clear":
                        await _clear_session(client, api_url, session_id)
                        continue

                    elif command == "/history":
                        await _show_history(client, api_url, session_id)
                        continue

                    elif command == "/session":
                        console.print(f"[dim]Session ID:[/dim] {session_id}")
                        continue

                    else:
                        console.print(f"[yellow]Unknown command: {user_input}[/yellow]")
                        console.print("[dim]Type /help for available commands[/dim]")
                        continue

                # Send message to agent
                console.print()
                if stream:
                    await _send_stream_message(client, api_url, agent, session_id, user_input)
                else:
                    await _send_message(client, api_url, agent, session_id, user_input)
                console.print()

            except httpx.ConnectError:
                console.print("[red]Error: Cannot connect to API.[/red]")
                console.print(f"[dim]Make sure the API is running at {api_url}[/dim]")
                console.print("[dim]Use /quit to exit or try again[/dim]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")


async def _send_message(client: httpx.AsyncClient, api_url: str, agent: str, session_id: str, message: str):
    """Send a non-streaming message."""
    url = f"{api_url}/api/v1/agents/run/{agent}"
    payload = {
        "user_input": message,
        "session_id": session_id,
    }

    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            result = data.get("result", {})
            content = result.get("data", {}).get("content", str(result))
            console.print(f"[bold green]Agent:[/bold green] {content}")
        else:
            console.print(f"[red]Error: {data.get('detail', 'Unknown error')}[/red]")

    except httpx.HTTPStatusError as e:
        detail = e.response.json().get("detail", {})
        console.print(f"[red]Error: {detail.get('message', str(e))}[/red]")


async def _send_stream_message(client: httpx.AsyncClient, api_url: str, agent: str, session_id: str, message: str):
    """Send a streaming message and display tokens as they arrive."""
    url = f"{api_url}/api/v1/agents/stream/{agent}"
    payload = {
        "user_input": message,
        "session_id": session_id,
    }

    try:
        full_response = ""
        console.print("[bold green]Agent:[/bold green] ", end="")

        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        chunk_data = json.loads(line[6:])
                        content = chunk_data.get("content", "")
                        done = chunk_data.get("done", False)

                        if content:
                            console.print(content, end="")
                            full_response += content

                        if done:
                            console.print()  # New line at end
                            break

                    except json.JSONDecodeError:
                        continue

        if not full_response:
            console.print("[dim](No response)[/dim]")

    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("detail", {})
            console.print(f"\n[red]Error: {detail.get('message', str(e))}[/red]")
        except Exception:
            console.print(f"\n[red]Error: {e}[/red]")


async def _show_history(client: httpx.AsyncClient, api_url: str, session_id: str):
    """Show conversation history."""
    url = f"{api_url}/api/v1/agents/history/{session_id}"

    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        messages = data.get("messages", [])
        if not messages:
            console.print("[dim]No conversation history.[/dim]")
            return

        table = Table(title="Conversation History", show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=4)
        table.add_column("Role", style="cyan", width=10)
        table.add_column("Message", style="white")

        for i, msg in enumerate(messages, 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # Truncate long messages
            if len(content) > 80:
                content = content[:77] + "..."
            table.add_row(str(i), role, content)

        console.print(table)

    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error retrieving history: {e}[/red]")


async def _clear_session(client: httpx.AsyncClient, api_url: str, session_id: str):
    """Clear session history."""
    url = f"{api_url}/api/v1/agents/history/{session_id}"

    try:
        response = await client.delete(url)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            console.print("[green]Session cleared successfully.[/green]")
        else:
            console.print(f"[yellow]{data.get('message', 'Session cleared.')}[/yellow]")

    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error clearing session: {e}[/red]")


def _show_help():
    """Display help for chat commands."""
    help_text = """
[bold]Available Commands:[/bold]

  [cyan]/help[/cyan]      Show this help message
  [cyan]/history[/cyan]   Show conversation history
  [cyan]/clear[/cyan]     Clear conversation history
  [cyan]/session[/cyan]   Show current session ID
  [cyan]/quit[/cyan]      Exit the chat (aliases: /exit, /q)

[bold]Tips:[/bold]
  - Use [cyan]--no-stream[/cyan] flag for non-streaming responses
  - Set [cyan]MAI_API_URL[/cyan] environment variable to change API endpoint
  - Use [cyan]--session[/cyan] to resume a previous conversation
"""
    console.print(Panel(help_text.strip(), title="[bold]Help[/bold]", border_style="blue"))


@main.group()
def agents():
    """Agent management commands."""
    pass


@agents.command("list")
@click.option("--api-url", envvar="MAI_API_URL", default=DEFAULT_API_URL, help="API base URL")
def list_agents(api_url: str):
    """List all available agents."""
    try:
        # First try the API endpoint
        response = httpx.get(f"{api_url}/api/v1/agents/", timeout=5.0)
        response.raise_for_status()
        data = response.json()

        agents_list = data.get("agents", [])
        _display_agents_table(agents_list)

    except httpx.ConnectError:
        console.print("[yellow]API not available, reading from local registry...[/yellow]")
        _list_agents_local()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print("[yellow]API endpoint not found, reading from local registry...[/yellow]")
            _list_agents_local()
        else:
            console.print(f"[red]Error: {e}[/red]")


def _list_agents_local():
    """List agents from local registry."""
    try:
        from src.core.agents.registry import agent_registry
        from src.core.agents.simple_agent import SimpleAgent

        # Ensure SimpleAgent is registered
        try:
            agent_registry.register_agent(SimpleAgent)
        except ValueError:
            pass  # Already registered

        agents_dict = agent_registry.list_agents()

        agents_list = []
        for name, agent_class in agents_dict.items():
            agents_list.append({
                "name": name,
                "description": getattr(agent_class, "description", "No description"),
            })

        _display_agents_table(agents_list)

    except Exception as e:
        console.print(f"[red]Error loading local registry: {e}[/red]")


def _display_agents_table(agents_list: list):
    """Display agents in a formatted table."""
    if not agents_list:
        console.print("[dim]No agents registered.[/dim]")
        return

    table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
    table.add_column("Agent", style="cyan")
    table.add_column("Description", style="white")

    for agent in agents_list:
        name = agent.get("name", "unknown")
        desc = agent.get("description", "No description")
        table.add_row(name, desc)

    console.print(table)


@main.group()
def tools():
    """Tool management commands."""
    pass


@tools.command("list")
@click.option("--api-url", envvar="MAI_API_URL", default=DEFAULT_API_URL, help="API base URL")
@click.option("--category", "-c", default=None, help="Filter by category")
def list_tools(api_url: str, category: Optional[str]):
    """List all available tools."""
    try:
        # First try the API endpoint
        url = f"{api_url}/api/v1/tools/"
        if category:
            url += f"?category={category}"

        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        tools_list = data.get("tools", [])
        _display_tools_table(tools_list)

    except httpx.ConnectError:
        console.print("[yellow]API not available, reading from local registry...[/yellow]")
        _list_tools_local(category)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            console.print("[yellow]API endpoint not found, reading from local registry...[/yellow]")
            _list_tools_local(category)
        else:
            console.print(f"[red]Error: {e}[/red]")


def _list_tools_local(category: Optional[str] = None):
    """List tools from local registry."""
    try:
        from src.core.tools.registry import tool_registry
        from src.core.tools import examples  # noqa: F401 - Import to register tools

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
            })

        _display_tools_table(tools_list)

    except Exception as e:
        console.print(f"[red]Error loading local registry: {e}[/red]")


def _display_tools_table(tools_list: list):
    """Display tools in a formatted table grouped by category."""
    if not tools_list:
        console.print("[dim]No tools registered.[/dim]")
        return

    # Group by category
    by_category: dict = {}
    for tool in tools_list:
        cat = tool.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)

    table = Table(title="Available Tools", show_header=True, header_style="bold cyan")
    table.add_column("Tool", style="cyan")
    table.add_column("Description", style="white")

    for category, cat_tools in sorted(by_category.items()):
        # Add category header
        table.add_row(f"[bold magenta]{category.title()}[/bold magenta]", "")

        for tool in cat_tools:
            name = f"  {tool.get('name', 'unknown')}"
            desc = tool.get("description", "No description")
            table.add_row(name, desc)

    console.print(table)


@main.command()
@click.option("--api-url", envvar="MAI_API_URL", default=DEFAULT_API_URL, help="API base URL")
def status(api_url: str):
    """Check API status and service health."""
    try:
        response = httpx.get(f"{api_url}/health", timeout=5.0)
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        services = data.get("services", {})

        # Status panel
        status_color = "green" if status == "healthy" else "red"
        header = Text()
        header.append(f"Status: ", style="dim")
        header.append(status.upper(), style=f"bold {status_color}")

        console.print(Panel(header, title="[bold]API Health[/bold]", border_style="blue"))

        # Services table
        if services:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Service", style="cyan")
            table.add_column("Status", style="white")

            for svc, connected in services.items():
                svc_status = "[green]Connected[/green]" if connected else "[red]Disconnected[/red]"
                table.add_row(svc, svc_status)

            console.print(table)

    except httpx.ConnectError:
        console.print("[red]Cannot connect to API[/red]")
        console.print(f"[dim]URL: {api_url}[/dim]")
        console.print("[dim]Make sure the API is running (docker-compose up -d)[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
