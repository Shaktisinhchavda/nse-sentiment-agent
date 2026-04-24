"""
Sentiment Analyzer for YouTube trading transcripts.
Uses OpenRouter LLM to extract stock-specific sentiment from video transcripts.
"""

import json
import logging
import re
from typing import Optional
from openai import OpenAI
from src.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

logger = logging.getLogger(__name__)

# Common NSE stock symbols for detection
NSE_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "ITC", "LT", "AXISBANK",
    "BAJFINANCE", "ASIANPAINT", "MARUTI", "TITAN", "SUNPHARMA",
    "NESTLEIND", "ULTRACEMCO", "WIPRO", "HCLTECH", "POWERGRID",
    "NTPC", "ONGC", "JSWSTEEL", "TATASTEEL", "TATAMOTORS",
    "ADANIENT", "ADANIPORTS", "BAJAJFINSV", "TECHM", "INDUSINDBK",
    "HINDALCO", "DRREDDY", "CIPLA", "COALINDIA", "BPCL",
    "GRASIM", "DIVISLAB", "BRITANNIA", "EICHERMOT", "APOLLOHOSP",
    "HDFC", "NIFTY", "SENSEX", "BANKNIFTY",
]

# Informal name to symbol mapping
STOCK_ALIASES = {
    "reliance": "RELIANCE", "jio": "RELIANCE", "mukesh": "RELIANCE",
    "tcs": "TCS", "tata consultancy": "TCS",
    "hdfc bank": "HDFCBANK", "hdfc": "HDFCBANK",
    "infosys": "INFY", "infy": "INFY",
    "icici": "ICICIBANK", "icici bank": "ICICIBANK",
    "hindustan unilever": "HINDUNILVR", "hul": "HINDUNILVR",
    "sbi": "SBIN", "state bank": "SBIN",
    "bharti airtel": "BHARTIARTL", "airtel": "BHARTIARTL",
    "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK",
    "itc": "ITC", "larsen": "LT", "l&t": "LT",
    "axis bank": "AXISBANK", "axis": "AXISBANK",
    "bajaj finance": "BAJFINANCE", "bajaj": "BAJFINANCE",
    "asian paints": "ASIANPAINT", "maruti": "MARUTI",
    "titan": "TITAN", "sun pharma": "SUNPHARMA",
    "wipro": "WIPRO", "hcl tech": "HCLTECH", "hcl": "HCLTECH",
    "tata motors": "TATAMOTORS", "tata steel": "TATASTEEL",
    "adani": "ADANIENT", "adani ports": "ADANIPORTS",
    "nifty": "NIFTY", "sensex": "SENSEX", "bank nifty": "BANKNIFTY",
}


class SentimentAnalyzer:
    """Analyze stock sentiment from video transcripts using LLM."""

    def __init__(self):
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY required")
        self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
        self.model = OPENROUTER_MODEL

    def analyze_transcript(self, transcript_text: str, video_info: dict) -> list[dict]:
        """
        Analyze a transcript for stock-specific sentiment.
        Returns list of sentiment entries per stock mentioned.
        """
        if not transcript_text or len(transcript_text.strip()) < 50:
            return []

        # Truncate very long transcripts
        text = transcript_text[:4000]
        channel = video_info.get("channel", "Unknown")
        title = video_info.get("title", "")

        prompt = f"""Analyze this Indian stock market YouTube video transcript for stock-specific sentiment.

Video Title: {title}
Channel: {channel}

Transcript (excerpt):
{text}

Extract ALL stocks/indices mentioned and their sentiment. Respond ONLY with valid JSON array:
[{{"symbol": "RELIANCE", "sentiment": "bullish", "confidence": 0.8, "reason": "brief reason"}}, ...]

Rules:
- Use NSE symbols (e.g. RELIANCE, TCS, HDFCBANK, NIFTY, SENSEX, BANKNIFTY)
- sentiment must be: "bullish", "bearish", or "neutral"
- confidence: 0.0 to 1.0
- If no stocks mentioned, return []
- Keep reasons under 50 words each"""

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a stock market sentiment analyst specializing in Indian equities (NSE/BSE). Extract precise sentiment per stock."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            content = resp.choices[0].message.content.strip()
            sentiments = self._parse_sentiment_json(content)

            # Enrich with video metadata
            for s in sentiments:
                s["channel"] = channel
                s["video_title"] = title
                s["video_url"] = video_info.get("url", "")
                s["video_id"] = video_info.get("id", "")

            logger.info("Analyzed '%s': %d stock sentiments", title[:40], len(sentiments))
            return sentiments

        except Exception as e:
            logger.warning("OpenRouter rate limit hit - falling back to rule-based sentiment extraction.")
            # Fallback: rule-based extraction
            return self._rule_based_sentiment(transcript_text, video_info)

    def _parse_sentiment_json(self, content: str) -> list[dict]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Strip markdown code blocks
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()

        try:
            data = json.loads(content)
            if isinstance(data, list):
                valid = []
                for item in data:
                    if isinstance(item, dict) and "symbol" in item:
                        item["symbol"] = item["symbol"].upper()
                        item.setdefault("sentiment", "neutral")
                        item.setdefault("confidence", 0.5)
                        item.setdefault("reason", "")
                        valid.append(item)
                return valid
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                try:
                    return self._parse_sentiment_json(match.group(0))
                except Exception:
                    pass
        return []

    def _rule_based_sentiment(self, text: str, video_info: dict) -> list[dict]:
        """Fallback rule-based sentiment when LLM fails."""
        text_lower = text.lower()
        results = []
        seen = set()

        bullish_words = {"buy", "bullish", "target", "breakout", "rally", "upside", "growth", "strong", "accumulate"}
        bearish_words = {"sell", "bearish", "crash", "fall", "downside", "weak", "avoid", "decline", "dump"}

        for alias, symbol in STOCK_ALIASES.items():
            if alias in text_lower and symbol not in seen:
                seen.add(symbol)
                # Count sentiment words near the mention
                bull = sum(1 for w in bullish_words if w in text_lower)
                bear = sum(1 for w in bearish_words if w in text_lower)
                if bull > bear:
                    sentiment, conf = "bullish", min(0.6, 0.3 + 0.1 * bull)
                elif bear > bull:
                    sentiment, conf = "bearish", min(0.6, 0.3 + 0.1 * bear)
                else:
                    sentiment, conf = "neutral", 0.3

                results.append({
                    "symbol": symbol, "sentiment": sentiment,
                    "confidence": conf, "reason": "Rule-based extraction",
                    "channel": video_info.get("channel", ""),
                    "video_title": video_info.get("title", ""),
                    "video_url": video_info.get("url", ""),
                    "video_id": video_info.get("id", ""),
                })
        return results

    def batch_analyze(self, videos_with_transcripts: list[dict], delay_sec: float = 12.0) -> list[dict]:
        """Analyze sentiment for a batch of videos with transcripts."""
        import time
        all_sentiments = []
        valid_videos = [v for v in videos_with_transcripts if v.get("transcript") and v["transcript"].get("text")]
        
        for i, video in enumerate(valid_videos):
            if i > 0 and delay_sec > 0:
                logger.info("Waiting %.1fs to respect OpenRouter free tier rate limits (8 requests/min)...", delay_sec)
                time.sleep(delay_sec)
                
            transcript = video.get("transcript")
            sentiments = self.analyze_transcript(transcript["text"], video)
            all_sentiments.extend(sentiments)
            
        logger.info("Total sentiment entries: %d from %d videos", len(all_sentiments), len(videos_with_transcripts))
        return all_sentiments
