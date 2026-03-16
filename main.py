"""
main.py — Terminal Chat Interface for the Agentic Sales Data Analyst
=====================================================================
Provides:
  - A welcome banner
  - An interactive input loop (while True)
  - Special commands: exit / quit, clear, help
  - Graceful handling of KeyboardInterrupt
"""

from agent import run_agent, clear_memory

# ═══════════════════════════════════════════════════════════════
# 1. WELCOME BANNER
# ═══════════════════════════════════════════════════════════════

BANNER = r"""
╔══════════════════════════════════════════╗
║   🤖 Agentic Sales Data Analyst v1.0    ║
║   Powered by LangChain + Gemini Flash   ║
╚══════════════════════════════════════════╝
Type 'help' for example questions, 'clear' to reset memory,
or 'exit' / 'quit' to leave.
"""

# ═══════════════════════════════════════════════════════════════
# 2. HELP TEXT — Example questions users can ask
# ═══════════════════════════════════════════════════════════════

HELP_TEXT = """
╔══════════════════════════════════════════════════════════════╗
║                    EXAMPLE QUESTIONS                        ║
╠══════════════════════════════════════════════════════════════╣
║ 1. Show me total sales by region for Q3 2023               ║
║ 2. Generate a bar chart of monthly sales for 2023          ║
║ 3. What is the average discount in the South region and    ║
║    does it violate our Q3 discount policy?                 ║
║ 4. Which product category has the highest profit margin?   ║
║ 5. Show me all Platinum discount orders in the East region ║
║    in Q4 2023 and tell me if they violate discount policy  ║
║ 6. Who are the top 5 sales reps by total sales in 2024?    ║
║ 7. What is the return rate by region and ship mode?        ║
╚══════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════
# 3. SEPARATOR for readability between exchanges
# ═══════════════════════════════════════════════════════════════

SEPARATOR = "\n" + "─" * 60 + "\n"

# ═══════════════════════════════════════════════════════════════
# 4. MAIN CHAT LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    """Run the interactive terminal chat loop."""
    print(BANNER)

    while True:
        try:
            user_input = input("You: ").strip()

            # Skip blank lines
            if not user_input:
                continue

            # --- Special command: exit / quit ---
            if user_input.lower() in ("exit", "quit"):
                print("\n👋 Goodbye! Happy analyzing.")
                break

            # --- Special command: clear ---
            if user_input.lower() == "clear":
                clear_memory()
                print("🧹 Memory cleared.")
                print(SEPARATOR)
                continue

            # --- Special command: help ---
            if user_input.lower() == "help":
                print(HELP_TEXT)
                print(SEPARATOR)
                continue

            # --- Normal query → send to the agent ---
            print("\n⏳ Thinking …\n")
            response = run_agent(user_input)
            print(f"Agent: {response}")
            print(SEPARATOR)

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted. Type 'exit' to quit.")
            continue


# ═══════════════════════════════════════════════════════════════
# 5. ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
