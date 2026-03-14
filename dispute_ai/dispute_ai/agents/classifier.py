from dispute_ai.state import CaseState
from dispute_ai.llm_client import call_llm

SYSTEM_PROMPT = """You are a payment dispute classifier for Indian merchants.

Given a chargeback notification, classify it into exactly one of these dispute types:
- item_not_received
- item_not_as_described
- unauthorized_transaction
- duplicate_charge
- subscription_cancelled

Return ONLY valid JSON. No markdown, no preamble, no text outside the JSON object:
{
  "dispute_type": "<one of the five types above>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining the classification>"
}"""


def run(state: CaseState) -> CaseState:
    user_prompt = (
        f"Chargeback Code: {state.chargeback_code}\n"
        f"Reason Text: {state.chargeback_reason}\n"
        f"Amount: {state.dispute_amount} {state.currency}\n"
        f"Customer: {state.customer_name}"
    )

    result = call_llm(SYSTEM_PROMPT, user_prompt, expect_json=True)

    state.dispute_type = result["dispute_type"]
    state.confidence_score = float(result["confidence"])
    state.classifier_reasoning = result["reasoning"]

    return state
