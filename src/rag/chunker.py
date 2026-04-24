"""
Smart Chunker for video transcripts and deal data.
Chunks by stock mention context windows for better retrieval.
"""

import re
import logging
from typing import Optional
from src.config import CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS_PER_VIDEO
from src.data.sentiment_analyzer import STOCK_ALIASES, NSE_SYMBOLS

logger = logging.getLogger(__name__)


def chunk_transcript(video: dict) -> list[dict]:
    """
    Chunk a video transcript into RAG-ready documents.
    Strategy: Split by stock mentions with surrounding context,
    then fill gaps with sliding-window chunks.
    """
    transcript = video.get("transcript")
    if not transcript or not transcript.get("text"):
        return []

    text = transcript["text"]
    channel = video.get("channel", "Unknown")
    title = video.get("title", "")
    url = video.get("url", "")
    video_id = video.get("id", "")
    segments = transcript.get("segments", [])

    chunks = []

    # Phase 1: Extract stock-mention chunks (high value)
    stock_chunks = _extract_stock_mention_chunks(text, video)
    chunks.extend(stock_chunks)

    # Phase 2: Sliding window for remaining content
    window_chunks = _sliding_window_chunks(text, video)
    chunks.extend(window_chunks)

    # Deduplicate and limit
    seen = set()
    unique = []
    for c in chunks:
        key = c["text"][:100]
        if key not in seen:
            seen.add(key)
            unique.append(c)

    unique = unique[:MAX_CHUNKS_PER_VIDEO]
    logger.debug("Chunked '%s': %d chunks", title[:40], len(unique))
    return unique


def _extract_stock_mention_chunks(text: str, video: dict) -> list[dict]:
    """Extract chunks centered around stock mentions."""
    chunks = []
    text_lower = text.lower()
    context_window = CHUNK_SIZE // 2  # chars before and after mention

    found_positions = []

    # Search for stock symbols and aliases
    for alias, symbol in STOCK_ALIASES.items():
        for match in re.finditer(re.escape(alias), text_lower):
            found_positions.append((match.start(), symbol, alias))

    for symbol in NSE_SYMBOLS:
        for match in re.finditer(r'\b' + re.escape(symbol) + r'\b', text, re.IGNORECASE):
            found_positions.append((match.start(), symbol, symbol))

    # Sort by position and deduplicate nearby mentions
    found_positions.sort(key=lambda x: x[0])
    filtered = []
    last_pos = -context_window * 2
    for pos, symbol, mention in found_positions:
        if pos - last_pos > context_window:
            filtered.append((pos, symbol, mention))
            last_pos = pos

    for pos, symbol, mention in filtered:
        start = max(0, pos - context_window)
        end = min(len(text), pos + context_window)
        chunk_text = text[start:end].strip()

        # Find approximate timestamp
        timestamp = _find_timestamp(pos, text, video.get("transcript", {}).get("segments", []))

        chunks.append({
            "text": f"[Stock: {symbol}] {chunk_text}",
            "metadata": {
                "source": "youtube",
                "type": "stock_mention",
                "symbol": symbol,
                "channel": video.get("channel", ""),
                "video_title": video.get("title", ""),
                "video_url": video.get("url", ""),
                "video_id": video.get("id", ""),
                "timestamp": timestamp,
                "mention": mention,
            },
        })

    return chunks


def _sliding_window_chunks(text: str, video: dict) -> list[dict]:
    """Create sliding window chunks from the full transcript."""
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    for i in range(0, len(text), step):
        chunk_text = text[i:i + CHUNK_SIZE].strip()
        if len(chunk_text) < 50:
            continue

        timestamp = _find_timestamp(i, text, video.get("transcript", {}).get("segments", []))

        chunks.append({
            "text": chunk_text,
            "metadata": {
                "source": "youtube",
                "type": "transcript_chunk",
                "channel": video.get("channel", ""),
                "video_title": video.get("title", ""),
                "video_url": video.get("url", ""),
                "video_id": video.get("id", ""),
                "timestamp": timestamp,
                "chunk_index": i // step,
            },
        })

    return chunks


def _find_timestamp(char_pos: int, full_text: str, segments: list[dict]) -> str:
    """Find approximate timestamp for a character position in transcript."""
    if not segments:
        return "0:00"

    # Estimate which segment this character falls in
    cumulative = 0
    for seg in segments:
        seg_text = seg.get("text", "")
        cumulative += len(seg_text) + 1  # +1 for space
        if cumulative >= char_pos:
            start = seg.get("start", 0)
            mins = int(start) // 60
            secs = int(start) % 60
            return f"{mins}:{secs:02d}"

    return "0:00"


def chunk_sentiment_data(sentiments: list[dict]) -> list[dict]:
    """Convert sentiment analysis results into RAG-ready chunks."""
    chunks = []
    for s in sentiments:
        text = (
            f"[Sentiment] {s['symbol']}: {s['sentiment']} "
            f"(confidence: {s.get('confidence', 0):.0%}) — "
            f"{s.get('reason', 'No reason given')}. "
            f"Source: {s.get('channel', 'Unknown')} — \"{s.get('video_title', '')}\""
        )
        chunks.append({
            "text": text,
            "metadata": {
                "source": "sentiment",
                "type": "sentiment_analysis",
                "symbol": s.get("symbol", ""),
                "sentiment": s.get("sentiment", ""),
                "confidence": s.get("confidence", 0),
                "channel": s.get("channel", ""),
                "video_title": s.get("video_title", ""),
                "video_url": s.get("video_url", ""),
                "video_id": s.get("video_id", ""),
            },
        })
    return chunks


def chunk_deals(deal_docs: list[dict]) -> list[dict]:
    """Pass-through for deal documents (already in chunk format)."""
    return deal_docs
