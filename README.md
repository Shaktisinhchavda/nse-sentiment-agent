# NSE/BSE Sentiment Chat Agent

> **CrowdWisdomTrading Intern Assessment** — A backend Python project using the Hermes Agent framework that provides sentiment analysis from 100 YouTube trading creators and NSE Bulk/Block deals data.

## 🎯 What It Does

1. **Fetches NSE Bulk & Block Deals** — Real-time deal data from NSE India (last 24 hours)
2. **Scrapes 100 YouTube Videos** — From Indian trading creators via Apify (last 24 hours)
3. **Extracts & Analyzes Transcripts** — Sentiment analysis per stock using LLM
4. **RAG-Powered Chatbot** — Answer questions grounded in real data with source citations
5. **Trading Recommendations** — With appropriate disclaimers
6. **Closed Learning Loop** — Improves responses based on user feedback (Hermes skill system)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│            Interactive Chat CLI              │
│     (RAG-powered, feedback learning loop)   │
├─────────────────────────────────────────────┤
│              Data Pipeline                   │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ NSE API  │ │  Apify   │ │ Sentiment  │  │
│  │ Deals    │ │ YouTube  │ │ Analyzer   │  │
│  └──────────┘ └──────────┘ └────────────┘  │
├─────────────────────────────────────────────┤
│         RAG (ChromaDB + Smart Chunking)     │
├─────────────────────────────────────────────┤
│         LLM: OpenRouter (free model)        │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/nse-sentiment-agent.git
cd nse-sentiment-agent
uv sync
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your keys:
#   OPENROUTER_API_KEY=your_key    (https://openrouter.ai/settings/keys)
#   APIFY_API_TOKEN=your_token     (https://console.apify.com/account/integrations)
```

### 3. Run Data Pipeline

```bash
uv run main.py pipeline
```

This fetches NSE deals, scrapes YouTube videos, extracts transcripts, analyzes sentiment, and indexes everything into the vector store.

### 4. Start Chatting

```bash
uv run main.py chat
```

Or run both in one go:

```bash
uv run main.py pipeline+chat
```

## 💬 Example Chat Session

```
You: What's the sentiment on RELIANCE?

Agent: Based on recent YouTube creator analysis, RELIANCE shows a **bullish** sentiment:

1. **CA Rachana Ranade** discusses Reliance's strong Q4 results and upside target
   of ₹2,800 [Source 1] — "Reliance Industries Q4" @ 3:42
2. **Akshat Shrivastava** highlights Jio's 5G expansion as a growth catalyst
   [Source 2] — "Top Stocks April 2026" @ 12:15
3. NSE Bulk Deal: Foreign institutional investor purchased 2.5L shares at ₹2,650
   [Source 3]

Overall: 3 bullish, 0 bearish, 1 neutral mention across 4 sources.

⚠️ This is based on YouTube creator sentiment and NSE deal data analysis,
not financial advice. Always do your own research.

─────────────────────────────────────────────
💡 Rate this response: /feedback good|bad|neutral [comment]
─────────────────────────────────────────────

You: Why are people bullish on HDFC Bank?

Agent: Creators are bullish on HDFCBANK for several reasons:

1. Strong credit growth and improving NIMs mentioned by **Vivek Bajaj**
   [Source 1] @ 5:20
2. Post-merger integration benefits highlighted by **Pranjal Kamra**
   [Source 2] @ 8:45
3. FII accumulation visible in recent block deals [Source 3]

Confidence: High (0.85) based on 5 consistent bullish mentions.

⚠️ Not financial advice. Consult a SEBI-registered advisor.

You: /feedback good Great answer with good citations!
✓ Feedback recorded: good
```

## 📁 Project Structure

```
nse-sentiment-agent/
├── main.py                      # CLI entry point
├── pyproject.toml               # Python dependencies (uv project file)
├── uv.lock                      # Exact package versions
├── .env.example                 # API key template
├── src/
│   ├── config.py                # Configuration & env vars
│   ├── data/
│   │   ├── nse_deals.py         # NSE Bulk/Block deals fetcher
│   │   ├── youtube_scraper.py   # Apify YouTube scraper
│   │   ├── transcript_fetcher.py# Video transcript extraction
│   │   ├── sentiment_analyzer.py# LLM-based sentiment analysis
│   │   └── pipeline.py          # Data pipeline orchestrator
│   ├── rag/
│   │   ├── chunker.py           # Smart chunking (stock-mention-centered)
│   │   ├── vector_store.py      # ChromaDB vector store
│   │   └── retriever.py         # RAG retrieval with citations
│   └── agent/
│       └── chat_agent.py        # RAG-powered chat agent
├── skills/                      # Hermes Agent skills
│   ├── nse-sentiment-chat/
│   │   └── SKILL.md             # Main skill definition
│   └── sentiment-learning-loop/
│       └── SKILL.md             # Learning loop skill
└── data/                        # Generated data (git-ignored)
    ├── chroma_db/               # Vector store
    ├── feedback/                # Feedback & learned context
    ├── nse_deals.json           # Cached NSE deals
    ├── youtube_videos.json      # Cached YouTube videos
    └── sentiments.json          # Extracted sentiments
```

## 🧠 Chunking Strategy

The RAG system uses a **dual-strategy chunking** approach:

1. **Stock-Mention-Centered Chunks** — When a stock symbol (e.g., RELIANCE, TCS) is detected in a transcript, a chunk is created centered on that mention with ±500 chars of context. This ensures the most relevant context around stock discussions is captured.

2. **Sliding Window Chunks** — The remaining transcript is chunked with a 1000-char window and 200-char overlap, ensuring no content is lost.

Each chunk includes metadata: source channel, video URL, timestamp, and stock symbol (if applicable).

## 🔄 Closed Learning Loop

The agent implements a **closed learning loop** using Hermes Agent's built-in skill system:

1. After each response, users can provide feedback (`/feedback good|bad|neutral [comment]`)
2. Negative feedback with corrections is persisted to `data/feedback/learned_context.txt`
3. On every new chat session, learned context is loaded and injected as system-level guidance
4. The agent progressively improves its responses based on accumulated feedback
5. Hermes skills (`skills/sentiment-learning-loop/SKILL.md`) document this mechanism

## 🔧 Technical Stack

| Component | Technology |
|-----------|-----------|
| Framework | Hermes Agent (skills system) |
| LLM | OpenRouter (`google/gemini-2.5-flash`) |
| YouTube Scraping | Apify (`streamers/youtube-scraper`) |
| NSE Data | Direct NSE API with session management |
| Vector DB | ChromaDB (local, persistent) |
| Transcripts | youtube-transcript-api + Apify fallback |
| CLI | Python (Rich formatting) |

## 📝 Approach

1. **No Mock Data** — All data is fetched live from NSE India and YouTube via Apify
2. **RAG over Full Context** — Uses retrieval-augmented generation to ground responses in actual data, avoiding hallucinations
3. **Source Citations** — Every response cites the YouTube channel, video title, and timestamp
4. **Smart Chunking** — Stock-mention-centered chunking ensures relevant context is retrieved
5. **Feedback Learning** — Persistent feedback loop progressively improves accuracy
6. **Graceful Fallbacks** — Multiple fallback paths (NSE API → jugaad-data, yt-transcript-api → Apify)

## ⚙️ Configuration

All configuration is in `.env`:

```env
OPENROUTER_API_KEY=your_key        # Required
APIFY_API_TOKEN=your_token         # Required
OPENROUTER_MODEL=google/gemini-2.5-flash  # Optional override
LOG_LEVEL=INFO                     # Optional: DEBUG, INFO, WARNING
```

## 📄 License

MIT

---

Built with ❤️ for CrowdWisdomTrading internship assessment.
