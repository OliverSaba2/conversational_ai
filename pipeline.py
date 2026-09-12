"""
Step 5: the end-to-end pipeline.

message -> identify_intent -> extract_entities -> decide_action -> generate_response
"""

from intents import identify_intent
from extraction import extract_entities
from actions import decide_action
from responses import generate_response


def process_message(message: str) -> dict:
    intent = identify_intent(message)
    entities = extract_entities(message)
    action_result = decide_action(intent, entities)
    reply = generate_response(intent, entities, action_result)

    structured_output = {
        "intent": intent,
        "doctor": entities.get("doctor"),
        "preferred_date": entities.get("preferred_date"),
        "preferred_time": entities.get("preferred_time"),
    }

    return {
        "structured_output": structured_output,
        "action": action_result,
        "reply": reply,
    }
