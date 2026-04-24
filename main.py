#!/usr/bin/env python3
"""
NSE/BSE Sentiment Chat Agent — Main Entry Point.
CrowdWisdomTrading Intern Assessment.

Usage:
    python main.py pipeline      # Run data ingestion pipeline
    python main.py chat          # Start interactive chat
    python main.py pipeline+chat # Run pipeline then chat
    python main.py stats         # Show current data stats
"""

import sys
import os
import logging

# Fix Windows console encoding
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import validate_config, logger


def run_pipeline(max_videos: int = 100):
    """Run the data ingestion pipeline."""
    from src.data.pipeline import DataPipeline
    pipeline = DataPipeline()
    stats = pipeline.run(max_videos=max_videos)
    return stats


def run_chat():
    """Start interactive chat session."""
    from src.agent.chat_agent import SentimentChatAgent
    from src.rag.retriever import Retriever
    from src.rag.vector_store import VectorStore

    store = VectorStore()
    if store.stats()["total_documents"] == 0:
        print("\n⚠️  No data in vector store. Run the pipeline first:")
        print("   python main.py pipeline\n")
        resp = input("Run pipeline now? (y/n): ").strip().lower()
        if resp == "y":
            run_pipeline()
        else:
            print("Starting chat with empty knowledge base...\n")

    retriever = Retriever(store)
    agent = SentimentChatAgent(retriever)

    print("\n" + "=" * 60)
    print("  🐂 NSE/BSE SENTIMENT CHAT AGENT")
    print("  Powered by CrowdWisdomTrading")
    print("=" * 60)
    print("\nAsk me about Indian stock market sentiment!")
    print("Examples:")
    print('  • "What\'s the sentiment on RELIANCE?"')
    print('  • "Why are people bullish on HDFC Bank?"')
    print('  • "What are FIIs doing?"')
    print('  • "Give me a market summary"')
    print('\nCommands:')
    print('  /summary  — Market sentiment summary')
    print('  /stats    — Show data statistics')
    print('  /feedback — Rate last response')
    print('  /clear    — Clear conversation')
    print('  /quit     — Exit')
    print("-" * 60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye! 👋")
            break

        if not user_input:
            continue

        # Handle commands
        cmd = user_input.lower()
        if cmd in ("/quit", "/exit", "quit", "exit"):
            print("Goodbye! 👋")
            break

        if cmd in ("/clear", "/reset"):
            agent.reset_history()
            print("✓ Conversation cleared.\n")
            continue

        if cmd in ("/stats",):
            stats = agent.get_stats()
            print("\n📊 Agent Statistics:")
            for k, v in stats.items():
                print(f"  {k}: {v}")
            print()
            continue

        if cmd.startswith("/feedback"):
            parts = user_input.split(maxsplit=2)
            if len(parts) < 2:
                print("Usage: /feedback good|bad|neutral [optional comment]")
                continue
            rating = parts[1].lower()
            comment = parts[2] if len(parts) > 2 else ""
            if rating not in ("good", "bad", "neutral"):
                print("Rating must be: good, bad, or neutral")
                continue
            agent.process_feedback(rating, comment)
            print(f"✓ Feedback recorded: {rating}")
            if rating == "bad" and comment:
                print("  📝 Learning from your feedback for future responses.")
            print()
            continue

        if cmd in ("/summary", "summary", "market summary"):
            user_input = "Give me a complete market sentiment summary of all stocks"

        # Get response
        print("\n🤔 Thinking...\n")
        response = agent.chat(user_input)
        print(f"Agent: {response}\n")
        print("─" * 60)
        print("💡 Rate this response: /feedback good|bad|neutral [comment]")
        print("─" * 60 + "\n")


def show_stats():
    """Show current data statistics."""
    from src.rag.vector_store import VectorStore
    from src.config import DATA_DIR

    store = VectorStore()
    stats = store.stats()

    print("\n📊 Data Statistics:")
    print(f"  Vector store documents: {stats['total_documents']}")

    # Check cached files
    for fname in ["nse_deals.json", "youtube_videos.json", "sentiments.json", "pipeline_stats.json"]:
        fpath = DATA_DIR / fname
        if fpath.exists():
            size = fpath.stat().st_size
            print(f"  {fname}: {size / 1024:.1f} KB")
        else:
            print(f"  {fname}: not found")
    print()


def main():
    """Main entry point."""
    # Validate configuration
    errors = validate_config()
    if errors:
        print("\n❌ Configuration errors:")
        for err in errors:
            print(f"  • {err}")
        print("\nCopy .env.example to .env and fill in your API keys:")
        print("  cp .env.example .env\n")
        sys.exit(1)

    # Parse command
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "pipeline":
        max_v = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        run_pipeline(max_videos=max_v)

    elif command == "chat":
        run_chat()

    elif command == "pipeline+chat":
        max_v = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        run_pipeline(max_videos=max_v)
        run_chat()

    elif command == "stats":
        show_stats()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
