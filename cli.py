"""
Interactive CLI for the Payment Collection AI Agent.
Uses Rich for a polished terminal experience.

Run with:
    python cli.py
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.rule import Rule
from rich import print as rprint

from agent import Agent


console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════╗[/bold cyan]
[bold cyan]║      Payment Collection AI Agent         ║[/bold cyan]
[bold cyan]║   Type your message and press Enter      ║[/bold cyan]
[bold cyan]║   Type 'quit' or 'exit' to end session   ║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════╝[/bold cyan]
"""


def format_agent_message(text: str) -> Panel:
    return Panel(
        Text(text, style="white"),
        title="[bold green]PayBot[/bold green]",
        border_style="green",
        padding=(0, 1),
    )


def format_user_message(text: str) -> Panel:
    return Panel(
        Text(text, style="white"),
        title="[bold blue]You[/bold blue]",
        border_style="blue",
        padding=(0, 1),
    )


def main():
    console.print(BANNER)
    console.print(Rule("[dim]New Session Started[/dim]"))
    console.print()

    agent = Agent()

    # Fire the greeting with a neutral first message
    console.print("[dim]Connecting...[/dim]")
    result = agent.next("hello")
    console.print()
    console.print(format_agent_message(result["message"]))
    console.print()

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session ended.[/dim]")
            break

        if user_input.strip().lower() in ("quit", "exit", "bye", "q"):
            console.print("\n[dim]Ending session. Goodbye! 👋[/dim]")
            break

        if not user_input.strip():
            continue

        console.print()
        console.print(format_user_message(user_input))
        console.print()

        with console.status("[dim]PayBot is typing...[/dim]", spinner="dots"):
            try:
                result = agent.next(user_input)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                continue

        console.print(format_agent_message(result["message"]))
        console.print()

        stage_keywords = ["have a great day", "session has been ended", "new session"]
        if any(kw in result["message"].lower() for kw in stage_keywords):
            console.print(Rule("[dim]Session Closed[/dim]"))
            break


if __name__ == "__main__":
    main()
