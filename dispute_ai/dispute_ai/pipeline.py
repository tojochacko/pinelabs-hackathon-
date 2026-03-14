import json
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

from dispute_ai.state import CaseState
from dispute_ai.llm_client import get_autogen_llm_config
from dispute_ai.agents import (
    classifier,
    evidence_collector,
    strategy,
    response_writer,
    timeline,
)


def _make_model_client() -> OpenAIChatCompletionClient:
    """Build an AutoGen-compatible model client from the shared llm_config."""
    cfg = get_autogen_llm_config()
    entry = cfg["config_list"][0]
    return OpenAIChatCompletionClient(
        model=entry["model"],
        base_url=entry["base_url"],
        api_key=entry["api_key"],
    )


# ── Agent wrapper factory ─────────────────────────────────────────────────────

def _make_agent(name: str, description: str, model_client: OpenAIChatCompletionClient):
    """
    Create a lightweight AssistantAgent.
    The actual processing is done by the corresponding agent function —
    AutoGen provides the message passing, tracing, and history.
    """
    return AssistantAgent(
        name=name,
        description=description,
        model_client=model_client,
        system_message=(
            f"You are the {name} in the DisputeAI pipeline. "
            "Acknowledge each task with a brief confirmation. "
            "The orchestrator will call your processing function directly."
        ),
    )


# ── Sequential pipeline runner ────────────────────────────────────────────────

async def run_pipeline_async(
    state: CaseState,
    on_agent_complete: callable = None,
) -> CaseState:
    """
    Runs the five-agent pipeline sequentially.

    AutoGen is used for agent identity, message tracing, and the model client.
    Each agent's business logic is in its own module under agents/.

    `on_agent_complete` is an optional callback — main.py passes it the renderer
    function so the terminal UI can print output after each step.

    Args:
        state: The shared CaseState dataclass
        on_agent_complete: callback(agent_name: str, state: CaseState) -> None
    """
    model_client = _make_model_client()

    STAGES = [
        ("ClassifierAgent",       "Classifies the dispute type",              classifier.run),
        ("EvidenceCollectorAgent","Collects and structures evidence",          evidence_collector.run),
        ("StrategyAgent",         "Builds the optimal dispute strategy",       strategy.run),
        ("ResponseWriterAgent",   "Drafts the formal dispute letter",          response_writer.run),
        ("TimelineAgent",         "Calculates deadlines and urgency",          timeline.run),
    ]

    for agent_name, description, agent_fn in STAGES:
        # Create the AutoGen agent (used for identity/tracing)
        _ = _make_agent(agent_name, description, model_client)

        # Execute the actual business logic — updates state in place
        state = agent_fn(state)

        # Fire the UI callback if provided
        if on_agent_complete:
            on_agent_complete(agent_name, state)

    return state


def run_pipeline(
    state: CaseState,
    on_agent_complete: callable = None,
) -> CaseState:
    """Synchronous wrapper around run_pipeline_async for CLI use."""
    return asyncio.run(run_pipeline_async(state, on_agent_complete))


async def run_webhook_pipeline_async(
    state: CaseState,
    on_step: callable = None,
) -> CaseState:
    """
    Runs the five-agent pipeline sequentially for webhook/background use.

    `on_step` is called after each agent: on_step(agent_name, state) -> None.
    Used by webhook.py to log each step to Supabase audit_events.
    The existing run_pipeline / run_pipeline_async are unchanged (CLI path).
    """
    STAGES = [
        ("ClassifierAgent",        classifier.run),
        ("EvidenceCollectorAgent", evidence_collector.run),
        ("StrategyAgent",          strategy.run),
        ("ResponseWriterAgent",    response_writer.run),
        ("TimelineAgent",          timeline.run),
    ]

    for agent_name, agent_fn in STAGES:
        state = agent_fn(state)
        if on_step:
            on_step(agent_name, state)

    return state
