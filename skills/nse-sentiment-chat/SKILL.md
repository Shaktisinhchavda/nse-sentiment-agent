---
name: nse-sentiment-chat
description: NSE/BSE sentiment analysis chatbot that analyzes 100+ YouTube trading creators and NSE bulk/block deals to answer stock sentiment questions with citations
version: 1.0.0
metadata:
  hermes:
    tags: [trading, sentiment, nse, bse, stocks, india]
    category: finance
    requires_toolsets: [terminal]
---

# NSE/BSE Sentiment Chat Agent

## When to Use
- When the user asks about Indian stock market sentiment
- When the user wants to know what YouTube trading creators think about a stock
- When the user asks about bulk/block deals on NSE
- When the user wants trading recommendations based on creator sentiment

## Procedure

### 1. Data Pipeline Setup
Run the data pipeline to fetch fresh data:
```bash
cd /path/to/nse-sentiment-agent
uv run main.py pipeline
```

This will:
- Fetch Bulk & Block deals from NSE (last 24 hours)
- Scrape 100 YouTube videos from Indian trading creators via Apify
- Extract transcripts from videos
- Analyze sentiment per stock using LLM
- Index all data into ChromaDB vector store

### 2. Start Chat
```bash
uv run main.py chat
```

### 3. Example Queries
- "What's the sentiment on RELIANCE?"
- "Why are people bullish on HDFC Bank?"
- "What are FIIs doing?"
- "Give me a market summary"
- "Should I buy TATA Motors?"

### 4. Feedback Loop
After each response, rate it:
- `/feedback good` — Response was helpful
- `/feedback bad "incorrect sentiment"` — Response was wrong (agent learns from this)
- `/feedback neutral` — Response was okay

The agent persists feedback and uses it to improve future responses.

## Architecture
- **Data Sources**: NSE API (bulk/block deals) + Apify YouTube Scraper
- **RAG**: ChromaDB vector store with smart chunking (stock-mention-centered)
- **LLM**: OpenRouter (any free model)
- **Learning Loop**: Feedback → learned_context.txt → injected into future prompts

## Pitfalls
- NSE API may rate-limit; the fetcher handles session cookies automatically
- YouTube transcript availability varies; ~60-70% of videos have transcripts
- Free OpenRouter models have rate limits; add delays between requests
- Apify free tier has $5/month credit limit

## Verification
1. Check `data/pipeline_stats.json` for pipeline run statistics
2. Run `uv run main.py stats` to see vector store document count
3. Ask a stock-specific question and verify source citations appear
