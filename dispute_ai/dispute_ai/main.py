import json
import sys
from pathlib import Path

from dispute_ai.state import CaseState
from dispute_ai.pipeline import run_pipeline
from dispute_ai.renderer import (
    console,
    render_banner,
    render_input_panel,
    render_agent_output,
    render_final_summary,
)


def main():
    data_path = Path(__file__).parent / "mock_data" / "chargebacks.json"
    all_cases = json.loads(data_path.read_text())

    target_id = sys.argv[1] if len(sys.argv) > 1 else "CB-2024-001"
    case = next((c for c in all_cases if c["case_id"] == target_id), None)

    if not case:
        console.print(f"[red]Error: Case ID '{target_id}' not found.[/red]")
        console.print(f"Available: {[c['case_id'] for c in all_cases]}")
        sys.exit(1)

    state = CaseState(**case)

    render_banner()
    render_input_panel(state)
    console.print()

    def on_agent_complete(agent_name: str, updated_state: CaseState):
        console.print(f"[green]✓[/green] {agent_name} complete")
        render_agent_output(agent_name, updated_state)

    state = run_pipeline(state, on_agent_complete=on_agent_complete)

    render_final_summary(state)


if __name__ == "__main__":
    main()
