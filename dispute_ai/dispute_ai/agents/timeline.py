from datetime import date
from dispute_ai.state import CaseState


def run(state: CaseState) -> CaseState:
    today = date.today()

    try:
        deadline = date.fromisoformat(state.filing_deadline)
    except ValueError:
        state.days_remaining    = -1
        state.urgency_level     = "UNKNOWN"
        state.recommended_action = "Could not parse deadline — verify filing date manually"
        return state

    state.days_remaining = (deadline - today).days

    if state.days_remaining < 0:
        state.urgency_level      = "EXPIRED"
        state.recommended_action = "Deadline has passed — escalate to legal team immediately"
    elif state.days_remaining <= 3:
        state.urgency_level      = "CRITICAL"
        state.recommended_action = "File TODAY — same business day, no exceptions"
    elif state.days_remaining <= 7:
        state.urgency_level      = "URGENT"
        state.recommended_action = "File within 48 hours"
    else:
        state.urgency_level      = "NORMAL"
        state.recommended_action = "File within 5 business days"

    reminders = []
    if state.days_remaining >= 7:
        reminders.append(f"Day {state.days_remaining - 5}: Prepare and review dispute letter")
    if state.days_remaining >= 3:
        reminders.append(f"Day {state.days_remaining - 2}: Final check — confirm all evidence attached")
    reminders.append(f"Day {state.days_remaining}:     *** FILING DEADLINE — confirm submission ***")

    state.reminder_schedule = reminders
    return state
