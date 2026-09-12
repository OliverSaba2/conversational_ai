"""
Run all the example patient messages from the brief through the pipeline
and print the structured output, the (mocked) action taken, and the reply.
"""

import json

from pipeline import process_message

EXAMPLE_MESSAGES = [
    "Can I see Dr. George tomorrow afternoon?",
    "Move my appointment from Monday to Wednesday.",
    "Cancel my appointment with Dr. Karim.",
    "What time does the clinic close?",
    "Do you have anything available after 5 tomorrow?",
    "I want to see my doctor again for the same problem.",
    "Book me Friday at 4 but don't confirm anything yet.",
    "I need an appointment sometime next week.",
    "Can somebody from the clinic call me?",
    # The ambiguous case called out in the brief: must NOT auto-book.
    "I might want to see Dr. George tomorrow at 4, but don't book anything yet.",
]

if __name__ == "__main__":
    for message in EXAMPLE_MESSAGES:
        result = process_message(message)
        print("=" * 70)
        print(f"Patient: {message}")
        print("Structured output:", json.dumps(result["structured_output"], indent=2))
        print("Action taken:", result["action"]["action"])
        print("Assistant reply:", result["reply"])
