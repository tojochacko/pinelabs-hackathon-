from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from dispute_ai.state import CaseState

console = Console()

URGENCY_COLOURS = {
    "CRITICAL": "bold red",
    "URGENT":   "bold yellow",
    "NORMAL":   "bold green",
    "EXPIRED":  "bold red blink",
    "UNKNOWN":  "bold white",
}

STRENGTH_COLOURS = {
    "strong":   "bold green",
    "moderate": "bold yellow",
    "weak":     "bold red",
}


def render_banner():
    console.print()
    console.rule("[bold]DisputeAI[/bold] · Autonomous Payment Dispute Resolution")
    console.print()


def render_input_panel(state: CaseState):
    content = (
        f"[bold]Case ID:[/bold]       {state.case_id}\n"
        f"[bold]Merchant:[/bold]      {state.merchant_id}\n"
        f"[bold]Customer:[/bold]      {state.customer_name}\n"
        f"[bold]Amount:[/bold]        {state.currency} {state.dispute_amount:,.2f}\n"
        f"[bold]Code:[/bold]          {state.chargeback_code}\n"
        f"[bold]Reason:[/bold]        {state.chargeback_reason}\n"
        f"[bold]Deadline:[/bold]      {state.filing_deadline}"
    )
    console.print(Panel(content, title="[bold white]📥 CHARGEBACK RECEIVED[/bold white]", border_style="white"))


def render_agent_output(agent_name: str, state: CaseState):
    """Dispatch to the correct render function based on agent name."""
    dispatch = {
        "ClassifierAgent":        _render_classifier,
        "EvidenceCollectorAgent": _render_evidence,
        "StrategyAgent":          _render_strategy,
        "ResponseWriterAgent":    _render_letter,
        "TimelineAgent":          _render_timeline,
    }
    fn = dispatch.get(agent_name)
    if fn:
        fn(state)
        console.print()


def _render_classifier(state: CaseState):
    content = (
        f"[bold]Dispute Type:[/bold]  [bold cyan]{state.dispute_type}[/bold cyan]\n"
        f"[bold]Confidence:[/bold]    [cyan]{state.confidence_score:.0%}[/cyan]\n"
        f"[bold]Reasoning:[/bold]     {state.classifier_reasoning}"
    )
    console.print(Panel(content, title="[bold cyan]🔍 AGENT 1 — CLASSIFIER[/bold cyan]", border_style="cyan"))


def _render_evidence(state: CaseState):
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold blue")
    table.add_column("Evidence Item", style="white", width=35)
    table.add_column("Value", style="cyan")

    for key, value in state.evidence.items():
        label = key.replace("_", " ").title()
        if isinstance(value, bool):
            display = "[green]✓ Yes[/green]" if value else "[red]✗ No[/red]"
        elif value is None:
            display = "[dim]—[/dim]"
        else:
            display = str(value)
        table.add_row(label, display)

    console.print(Panel(table, title="[bold blue]📋 AGENT 2 — EVIDENCE COLLECTOR[/bold blue]", border_style="blue"))


def _render_strategy(state: CaseState):
    strength_colour = STRENGTH_COLOURS.get(state.argument_strength, "white")
    rec_colour = "green" if state.recommendation == "file_dispute" else "yellow"
    content = (
        f"[bold]Strength:[/bold]       [{strength_colour}]{state.argument_strength.upper()}[/{strength_colour}]\n"
        f"[bold]Recommendation:[/bold] [{rec_colour}]{state.recommendation}[/{rec_colour}]\n"
        f"[bold]Argument:[/bold]       {state.winning_argument}\n"
        f"[bold]Key Evidence:[/bold]   {', '.join(state.key_evidence_refs)}"
    )
    console.print(Panel(content, title="[bold yellow]⚖️  AGENT 3 — STRATEGY[/bold yellow]", border_style="yellow"))


def _render_letter(state: CaseState):
    if state.recommendation != "file_dispute":
        content = (
            f"[yellow]Letter not generated.[/yellow]\n\n"
            f"[bold]Recommendation:[/bold] {state.recommendation}\n\n"
            f"{state.dispute_letter}"
        )
        console.print(Panel(content, title="[bold yellow]✍️  AGENT 4 — RESPONSE WRITER[/bold yellow]", border_style="yellow"))
    else:
        preview = state.dispute_letter[:600] + "\n\n[dim]... (full letter saved to output/)[/dim]"
        console.print(Panel(preview, title="[bold green]✍️  AGENT 4 — RESPONSE WRITER[/bold green]", border_style="green"))


def _render_timeline(state: CaseState):
    urgency_colour = URGENCY_COLOURS.get(state.urgency_level, "white")
    reminders_text = "\n".join(f"  • {r}" for r in state.reminder_schedule)
    content = (
        f"[bold]Days Remaining:[/bold]  [{urgency_colour}]{state.days_remaining} days[/{urgency_colour}]\n"
        f"[bold]Urgency:[/bold]         [{urgency_colour}]{state.urgency_level}[/{urgency_colour}]\n"
        f"[bold]Action:[/bold]          {state.recommended_action}\n\n"
        f"[bold]Reminder Schedule:[/bold]\n{reminders_text}"
    )
    console.print(Panel(content, title="[bold magenta]📅 AGENT 5 — TIMELINE[/bold magenta]", border_style="magenta"))


def render_final_summary(state: CaseState):
    strength_colour = STRENGTH_COLOURS.get(state.argument_strength, "white")
    urgency_colour  = URGENCY_COLOURS.get(state.urgency_level, "white")
    rec_colour      = "green" if state.recommendation == "file_dispute" else "yellow"
    content = (
        f"  [bold]Case:[/bold]           {state.case_id}\n"
        f"  [bold]Dispute Type:[/bold]   {state.dispute_type}\n"
        f"  [bold]Case Strength:[/bold]  [{strength_colour}]{state.argument_strength.upper()}[/{strength_colour}]\n"
        f"  [bold]Decision:[/bold]       [{rec_colour}]{state.recommendation}[/{rec_colour}]\n"
        f"  [bold]Urgency:[/bold]        [{urgency_colour}]{state.urgency_level} — {state.days_remaining} days[/{urgency_colour}]\n"
        f"  [bold]Letter:[/bold]         output/{state.case_id}_letter.txt\n"
    )
    console.print()
    console.print(Panel(content, title="[bold] ✅  PIPELINE COMPLETE [/bold]", border_style="white", padding=(1, 2)))
    console.print()
