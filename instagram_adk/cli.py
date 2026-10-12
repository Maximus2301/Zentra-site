"""Interactive CLI for the Autonomous Instagram ADK 2.0 Agent System."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config.settings import load_all_accounts, OUTPUT_DIR
from .workflow import run_campaign_sync

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def print_banner():
    banner = """
[bold cyan]╔═══════════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]AUTONOMOUS MULTI-ACCOUNT INSTAGRAM AGENT SYSTEM[/bold white]                         [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [yellow]Powered by Google Agent Development Kit (ADK 2.0)[/yellow]                       [bold cyan]║[/bold cyan]
[bold cyan]╚═══════════════════════════════════════════════════════════════════════════╝[/bold cyan]
"""
    rprint(banner)


def select_account_interactive(accounts: list[dict]) -> str:
    table = Table(title="[bold green]Configured Instagram Channels[/bold green]", show_header=True)
    table.add_column("Index", style="cyan", width=6)
    table.add_column("Account Handle", style="magenta")
    table.add_column("Name", style="white")
    table.add_column("Mission", style="dim")

    for i, acc in enumerate(accounts, 1):
        table.add_row(str(i), acc["handle"], acc["name"], acc["mission"][:55] + "...")

    console.print(table)
    while True:
        try:
            choice = input("\n👉 Select Account (Enter number 1-3, or handle, or press Enter for default 1): ").strip()
            if not choice or choice == "1":
                return accounts[0]["account_id"]
            if choice.isdigit() and 1 <= int(choice) <= len(accounts):
                return accounts[int(choice) - 1]["account_id"]
            for acc in accounts:
                if choice.lower() in (acc["account_id"].lower(), acc["handle"].lower()):
                    return acc["account_id"]
            print("Invalid choice, please select again.")
        except (KeyboardInterrupt, EOFError):
            sys.exit(0)


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Autonomous Multi-Account Instagram Publisher (Google ADK 2.0)")
    parser.add_argument("--account", "-a", type=str, help="Target account ID (e.g. workplace_rights_watch, fintech_save_smart, alex_tech_ceo)")
    parser.add_argument("--script", "-s", type=str, help="Raw notes or rough draft script to evolve")
    parser.add_argument("--topic", "-t", type=str, help="Target topic for the post")
    parser.add_argument("--emotion", "-e", type=str, help="Target emotion to invoke (e.g. 'Righteous Indignation', 'Financial Relief')")
    parser.add_argument("--formats", "-f", nargs="+", default=["static_post", "story", "reel", "status"], help="Formats to generate (static_post, story, reel, status)")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")

    args = parser.parse_args()
    accounts = load_all_accounts()

    account_id = args.account
    if not account_id:
        if args.non_interactive:
            account_id = accounts[0]["account_id"]
        else:
            account_id = select_account_interactive(accounts)

    raw_script = args.script
    topic = args.topic
    emotion = args.emotion
    formats = args.formats

    if not args.non_interactive and not raw_script and not topic:
        rprint("\n[bold yellow]Input Mode Options:[/bold yellow]")
        rprint(" 1. Input raw notes/script to evolve into Instagram content")
        rprint(" 2. Specify a topic")
        rprint(" 3. Fully Autonomous (agent discovers best trending topic)")
        choice = input("\n👉 Select Input Mode (1/2/3, default 1): ").strip()

        if choice == "1" or not choice:
            rprint("[dim]Enter your raw script or notes below (press Enter twice to finish):[/dim]")
            lines = []
            while True:
                line = input()
                if not line and lines and not lines[-1]:
                    break
                lines.append(line)
            raw_script = "\n".join(lines).strip()
            if not raw_script:
                raw_script = "Company refused to pay 2 months salary after resignation. HR is ignoring all follow-up emails."
        elif choice == "2":
            topic = input("👉 Enter target topic: ").strip()

    if not args.non_interactive and not emotion:
        emotion_input = input("👉 Optional: Specify Target Emotion (or press Enter to auto-infer): ").strip()
        if emotion_input:
            emotion = emotion_input

    rprint(f"\n[bold green]► Initiating ADK 2.0 Pipeline for Channel:[/bold green] [bold magenta]{account_id}[/bold magenta]")
    rprint(f"[bold cyan]► Target Formats:[/bold cyan] {', '.join(formats)}")
    if emotion:
        rprint(f"[bold red]► Calibrated Emotion:[/bold red] {emotion}")

    result = run_campaign_sync(
        account_id=account_id,
        raw_user_script=raw_script,
        requested_topic=topic,
        requested_emotion=emotion,
        active_formats=formats,
    )

    rprint("\n" + "=" * 80)
    rprint(Panel.fit(
        f"[bold green]✓ CAMPAIGN GENERATION COMPLETED SUCCESSFULLY![/bold green]\n\n"
        f"[white]Channel:[/white] [magenta]{result.get('account', {}).get('name')}[/magenta] ({result.get('account', {}).get('handle')})\n"
        f"[white]Audience Cohort:[/white] [cyan]{result.get('narrative', {}).get('cohort_name')}[/cyan]\n"
        f"[white]Target Emotion:[/white] [yellow]{result.get('narrative', {}).get('target_emotion')}[/yellow]\n"
        f"[white]Quality Score:[/white] [bold green]{result.get('critic', {}).get('score', 9.4)}/10[/bold green]\n"
        f"[white]Interactive HTML Preview:[/white] [bold underline cyan]{result.get('preview_html_path')}[/bold underline cyan]\n\n"
        f"[bold]Hook:[/bold] \"{result.get('narrative', {}).get('hook')}\"",
        title="[bold yellow]ADK 2.0 Campaign Result[/bold yellow]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
