"""
Sentiment Chat Agent — RAG-powered chatbot for Indian stock sentiment.
Uses OpenRouter LLM with retrieved context to answer questions.
Implements a closed learning loop via feedback persistence.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from src.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    FEEDBACK_DIR, DATA_DIR,
)
from src.rag.retriever import Retriever

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Indian stock market sentiment analyst for CrowdWisdomTrading.
You analyze sentiment from YouTube trading creators and NSE Bulk/Block deals data.

RULES:
1. ONLY answer based on the provided RELEVANT DATA context. Never make up information.
2. Always cite your sources using [Source N] references.
3. If the data doesn't contain information about a topic, say so clearly.
4. When giving trading recommendations, always include disclaimers.
5. Mention the YouTube channel name and timestamp when citing video sources.
6. Be specific about sentiment direction (bullish/bearish/neutral) and confidence.
7. For FII/DII questions, reference bulk/block deal data.

CAPABILITIES:
- Answer questions about stock sentiment (e.g., "What's the sentiment on RELIANCE?")
- Explain why people are bullish/bearish on specific stocks
- Summarize what trading creators are saying
- Provide FII/DII activity insights from deal data
- Give trading recommendations with appropriate disclaimers

DISCLAIMER TEMPLATE (use when giving recommendations):
"⚠️ This is based on YouTube creator sentiment and NSE deal data analysis, not financial advice.
Always do your own research and consult a SEBI-registered advisor before trading."
"""


class SentimentChatAgent:
    """RAG-powered chat agent for Indian stock market sentiment."""

    def __init__(self, retriever: Retriever = None):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required")

        self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
        self.model = OPENROUTER_MODEL
        self.retriever = retriever or Retriever()
        self.history: list[dict] = []
        self.feedback_log: list[dict] = []
        self._load_learned_context()

        logger.info("Chat agent initialized with model: %s", self.model)

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return a response.
        Uses RAG to ground responses in actual data.
        """
        # Retrieve relevant context
        context = self.retriever.retrieve(user_message)

        # Check for special commands
        if user_message.strip().lower() in ("/summary", "summary", "market summary"):
            summary = self.retriever.get_sentiment_summary()
            context = summary + "\n\n" + context

        # Build messages with context
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add learned context from feedback
        if self._learned_context:
            messages.append({
                "role": "system",
                "content": f"LEARNED FROM PREVIOUS FEEDBACK:\n{self._learned_context}",
            })

        # Add conversation history (last 10 exchanges)
        for msg in self.history[-20:]:
            messages.append(msg)

        # Add current message with RAG context
        augmented_message = f"""User Question: {user_message}

{context}

Based on the above data, provide a comprehensive answer with source citations."""

        messages.append({"role": "user", "content": augmented_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
            )
            answer = response.choices[0].message.content.strip()

            # Update history
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": answer})

            return answer

        except Exception as e:
            logger.error("LLM chat failed: %s", e)
            return f"Sorry, I encountered an error: {e}. Please try again."

    def process_feedback(self, rating: str, comment: str = ""):
        """
        Process user feedback on the last response.
        This implements the 'closed learning loop' — feedback is persisted
        and used to improve future responses.

        Args:
            rating: 'good', 'bad', or 'neutral'
            comment: Optional feedback comment
        """
        if len(self.history) < 2:
            return

        last_q = self.history[-2].get("content", "")
        last_a = self.history[-1].get("content", "")

        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "question": last_q,
            "answer": last_a[:500],
            "rating": rating,
            "comment": comment,
        }

        self.feedback_log.append(feedback_entry)
        self._save_feedback(feedback_entry)

        # If negative feedback, learn from it
        if rating == "bad" and comment:
            self._learn_from_feedback(feedback_entry)

        logger.info("Feedback recorded: %s — %s", rating, comment[:50] if comment else "no comment")

    def _learn_from_feedback(self, feedback: dict):
        """
        Update learned context based on negative feedback.
        This is the 'closed learning loop' mechanism.
        """
        learned_file = FEEDBACK_DIR / "learned_context.txt"
        entry = (
            f"\n- When asked about '{feedback['question'][:100]}', "
            f"user feedback: {feedback['comment'][:200]}"
        )
        try:
            with open(learned_file, "a", encoding="utf-8") as f:
                f.write(entry)
            self._learned_context += entry
            logger.info("Learned from feedback: %s", entry[:80])
        except Exception as e:
            logger.warning("Failed to save learned context: %s", e)

    def _load_learned_context(self):
        """Load previously learned context from feedback."""
        learned_file = FEEDBACK_DIR / "learned_context.txt"
        self._learned_context = ""
        if learned_file.exists():
            try:
                self._learned_context = learned_file.read_text(encoding="utf-8")
                logger.info("Loaded learned context (%d chars)", len(self._learned_context))
            except Exception:
                pass

    def _save_feedback(self, entry: dict):
        """Save feedback entry to disk."""
        feedback_file = FEEDBACK_DIR / "feedback_log.jsonl"
        try:
            with open(feedback_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to save feedback: %s", e)

    def reset_history(self):
        """Clear conversation history."""
        self.history = []
        logger.info("Conversation history cleared")

    def get_stats(self) -> dict:
        """Get agent statistics."""
        store_stats = self.retriever.store.stats()
        return {
            "model": self.model,
            "history_length": len(self.history),
            "feedback_count": len(self.feedback_log),
            "learned_context_size": len(self._learned_context),
            **store_stats,
        }
