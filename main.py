"""
CLI chat entry point. Run with: python main.py
'quit'/'exit' (or Ctrl+C) to stop, 'reset' to drop the current request.
"""

import json

from session import ConversationSession


def main():
    print("CliniKit assistant - type a patient message (or 'quit' to exit, 'reset' to start over).\n")
    session = ConversationSession()
    print(f"Assistant: {session.opening_message()}\n")

    while True:
        try:
            message = input("Patient: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not message:
            continue
        if message.lower() in ("quit", "exit"):
            break
        if message.lower() == "reset":
            session.reset()
            print("Assistant: Sure, starting fresh.\n")
            continue

        result = session.handle_message(message)
        print("Structured output:", json.dumps(result["structured_output"], indent=2))
        print("Action taken:", result["action"]["action"])
        print(f"Assistant: {result['reply']}\n")


if __name__ == "__main__":
    main()
