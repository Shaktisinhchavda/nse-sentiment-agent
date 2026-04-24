"""
RAG Retriever — queries the vector store and formats context for the LLM.
"""

import logging
import re
from src.rag.vector_store import VectorStore
from src.data.sentiment_analyzer import STOCK_ALIASES, NSE_SYMBOLS
from src.config import TOP_K_RESULTS

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieve and format relevant context from the vector store."""

    def __init__(self, vector_store: VectorStore = None):
        self.store = vector_store or VectorStore()

    def retrieve(self, query: str, top_k: int = None) -> str:
        """
        Retrieve relevant context for a user query.
        Returns a formatted string with sources cited.
        """
        k = top_k or TOP_K_RESULTS

        # Detect stock symbols in the query
        symbol = self._detect_symbol(query)

        # Query with symbol filter if detected
        results = self.store.query(query, top_k=k, symbol_filter=symbol)

        if not results:
            # Broaden search without symbol filter
            results = self.store.query(query, top_k=k)

        if not results:
            return "No relevant data found in the knowledge base."

        # Format results with citations
        context_parts = []
        sources = []
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            text = r.get("text", "")
            source_type = meta.get("source", "unknown")
            channel = meta.get("channel", "")
            video_title = meta.get("video_title", "")
            video_url = meta.get("video_url", "")
            timestamp = meta.get("timestamp", "")

            context_parts.append(f"[Source {i}] {text}")

            # Build citation
            if source_type == "youtube" or source_type == "sentiment":
                cite = f"[{i}] {channel}"
                if video_title:
                    cite += f" — \"{video_title}\""
                if timestamp and timestamp != "0:00":
                    cite += f" @ {timestamp}"
                if video_url:
                    cite += f" ({video_url})"
            elif source_type == "NSE":
                cite = f"[{i}] NSE {meta.get('type', 'deal')} — {meta.get('date', 'today')}"
            else:
                cite = f"[{i}] {source_type}"
            sources.append(cite)

        context = "\n\n".join(context_parts)
        citations = "\n".join(sources)

        return f"RELEVANT DATA:\n{context}\n\nSOURCES:\n{citations}"

    def retrieve_for_symbol(self, symbol: str) -> str:
        """Retrieve all data for a specific stock symbol."""
        symbol = symbol.upper()
        results = self.store.query(
            f"sentiment analysis {symbol} stock trading",
            top_k=TOP_K_RESULTS * 2,
            symbol_filter=symbol,
        )
        if not results:
            return f"No data found for {symbol}."

        context_parts = []
        for r in results:
            context_parts.append(r.get("text", ""))

        return f"Data for {symbol}:\n" + "\n".join(context_parts)

    def get_sentiment_summary(self) -> str:
        """Get a high-level summary of all sentiments in the store."""
        # Query for general sentiment data
        results = self.store.query(
            "stock market sentiment bullish bearish analysis",
            top_k=20,
        )
        if not results:
            return "No sentiment data available yet. Run data pipeline first."

        # Aggregate by symbol
        symbol_sentiments = {}
        for r in results:
            meta = r.get("metadata", {})
            symbol = meta.get("symbol", "")
            sentiment = meta.get("sentiment", "")
            if symbol and sentiment:
                if symbol not in symbol_sentiments:
                    symbol_sentiments[symbol] = {"bullish": 0, "bearish": 0, "neutral": 0}
                if sentiment in symbol_sentiments[symbol]:
                    symbol_sentiments[symbol][sentiment] += 1

        if not symbol_sentiments:
            return "Sentiment data found but no structured sentiments extracted."

        lines = ["Stock Sentiment Summary:"]
        for sym, counts in sorted(symbol_sentiments.items()):
            total = sum(counts.values())
            dominant = max(counts, key=counts.get)
            lines.append(f"  {sym}: {dominant.upper()} ({counts['bullish']}↑ {counts['bearish']}↓ {counts['neutral']}→) from {total} mentions")

        return "\n".join(lines)

    def _detect_symbol(self, query: str) -> str | None:
        """Detect a stock symbol mentioned in the query."""
        query_lower = query.lower()

        # Check direct symbol mentions
        for symbol in NSE_SYMBOLS:
            if re.search(r'\b' + re.escape(symbol) + r'\b', query, re.IGNORECASE):
                return symbol

        # Check aliases
        for alias, symbol in STOCK_ALIASES.items():
            if alias in query_lower:
                return symbol

        return None
