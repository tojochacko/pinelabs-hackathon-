import json
from pathlib import Path
from dispute_ai.state import CaseState
from dispute_ai.llm_client import call_llm

SYSTEM_PROMPT = """You are a specialist in payment dispute resolution for Indian merchants.

Write a formal chargeback dispute response letter addressed to the acquiring bank.

Requirements:
- Formal tone throughout
- Structure exactly as follows:
  (1) Reference & Subject line
  (2) Statement of Facts
  (3) Evidence Summary — cite each piece of evidence by name
  (4) Legal Basis — reference the chargeback code and applicable RBI guidelines
  (5) Request for Reversal — clear, direct, unambiguous
- Length: 300-400 words
- Plain text only — absolutely no markdown, no # headers, no bullet points, no asterisks
- Professional Indian banking correspondence style"""


def run(state: CaseState) -> CaseState:
    if state.recommendation != "file_dispute":
        # Do not generate a letter for weak cases — output settlement rationale instead
        state.dispute_letter = (
            f"[Letter not generated — Strategy Agent recommends: {state.recommendation}]\n\n"
            f"Rationale: {state.winning_argument}"
        )
        return state

    user_prompt = (
        f"Case ID: {state.case_id}\n"
        f"Merchant: {state.merchant_id}\n"
        f"Customer: {state.customer_name}\n"
        f"Amount: {state.dispute_amount} {state.currency}\n"
        f"Chargeback Code: {state.chargeback_code}\n"
        f"Dispute Type: {state.dispute_type}\n"
        f"Filing Deadline: {state.filing_deadline}\n\n"
        f"Strategy:\n{state.winning_argument}\n\n"
        f"Evidence Available:\n{json.dumps(state.evidence, indent=2)}"
    )

    state.dispute_letter = call_llm(
        SYSTEM_PROMPT,
        user_prompt,
        expect_json=False,
        max_tokens=1000,
    )

    # Persist letter to output/
    output_dir = Path(__file__).parent.parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{state.case_id}_letter.txt"
    output_path.write_text(state.dispute_letter)

    return state
