import json
from dispute_ai.state import CaseState
from dispute_ai.llm_client import call_llm

SYSTEM_PROMPT = """You are a payment dispute strategist for Indian merchants.

Given a dispute type and an evidence bundle, determine the optimal strategy.

Rules:
1. If evidence strongly supports the merchant → recommend filing the dispute.
2. If evidence is mixed → recommend filing but flag risks clearly.
3. If evidence does NOT support the merchant → honestly recommend settling with the customer.
   Do NOT recommend filing a dispute you cannot win. Filing a losing dispute costs the
   merchant more than settling directly.

Return ONLY valid JSON. No markdown, no preamble:
{
  "winning_argument": "<2-3 sentence argument summarising the merchant's strongest position>",
  "argument_strength": "<strong|moderate|weak>",
  "key_evidence_refs": ["<evidence key 1>", "<evidence key 2>"],
  "recommendation": "<file_dispute|settle_with_customer|escalate_to_legal>",
  "win_probability": <integer 0-100>,
  "pipeline_decision": "<FIGHT|ACCEPT>"
}"""


def run(state: CaseState) -> CaseState:
    user_prompt = (
        f"Dispute Type: {state.dispute_type} (confidence: {state.confidence_score:.0%})\n"
        f"Dispute Amount: {state.dispute_amount} {state.currency}\n"
        f"Evidence Bundle:\n{json.dumps(state.evidence, indent=2)}"
    )

    result = call_llm(SYSTEM_PROMPT, user_prompt, expect_json=True)

    state.winning_argument  = result["winning_argument"]
    state.argument_strength = result["argument_strength"]
    state.key_evidence_refs = result["key_evidence_refs"]
    state.recommendation    = result["recommendation"]
    state.win_probability   = result.get("win_probability", 0)
    state.pipeline_decision = result.get("pipeline_decision", "")

    return state
