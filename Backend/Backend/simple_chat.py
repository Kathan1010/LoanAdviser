"""
Simple terminal chatbot using the LLMService.

Requirements:
- .env file with GEMINI_API_KEY set
- Dependencies from requirements.txt installed

Run:
    python3 simple_chat.py

Type 'exit' or press Ctrl+C to quit.
"""

import sys
from llm_service import LLMService, ConversationMessage


def main():
    session_id = "cli"
    llm = LLMService()

    print("🤖 Multilingual Loan Assistant (CLI)")
    print("Type 'exit' to quit.\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in {"exit", "quit"}:
                print("Bot: Goodbye!")
                break
            if not user_input:
                continue

            # Add user message to history
            llm.add_to_history(session_id, "user", user_input)
            history = llm.get_history(session_id, limit=10)

            # Generate response (general conversation only)
            response = llm.generate_response(
                user_message=user_input,
                conversation_history=history,
                eligibility_context=None,
                session_id=session_id,
            )

            # Add bot response to history
            llm.add_to_history(session_id, "assistant", response)

            print(f"Bot: {response}\n")
    except KeyboardInterrupt:
        print("\nBot: Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()

