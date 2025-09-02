
STATES = [
    "New Contact",
    "Wait Answer",
    "No Answer",
    "Wait No Answer Reminder",
    "Wait Postpone Reminder",
    "Wait Follow-up Reminder",
    "Message Arrived",
] 

INITIAL_STATE = STATES[0]

TRANSITIONS = {
    ("New Contact",              "Send Mail"):       "Wait Answer",
    ("Wait Answer",              "No Answer"):       "No Answer",
    ("No Answer",                "Send Reminder"):   "Wait No Answer Reminder",
    ("Wait No Answer Reminder",  "Send Mail"):       "Wait Answer",
    ("Wait Postpone Reminder",   "Send Mail"):       "Wait Answer",
    ("Wait Answer",              "Message Arrived"): "Message Arrived",
    ("Message Arrived",          "Postpone"):        "Wait Postpone Reminder",
    ("Message Arrived",          "Send Mail"):       "Wait Answer",
    ("Wait Answer",              "Send Follow-up"):  "Wait Follow-up Reminder",
    ("Wait Follow-up Reminder",  "Send Mail"):       "Wait Answer",
}
def _possible_events(state: str):
    TRANSITIONS.keys()
    return [e for (s, e) in TRANSITIONS.keys() if s == state]


def _run_state_machine(state: str, event: str) :
    next_state = TRANSITIONS.get((state, event))
    if not next_state:
        return False
    return next_state


# print(_possible_events("Wait Answer"))