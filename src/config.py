"""
Configuration module for the NSE Sentiment Agent.

Loads environment variables and provides centralized configuration.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
load_dotenv(_project_root / ".env")

# ─── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s │ %(name)-28s │ %(levelname)-7s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nse_sentiment")

# ─── API Keys ──────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# ─── LLM Configuration ────────────────────────────────────────────────────────
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")

# ─── Data Directories ─────────────────────────────────────────────────────────
DATA_DIR = _project_root / "data"
DATA_DIR.mkdir(exist_ok=True)
CHROMA_DIR = DATA_DIR / "chroma_db"
CHROMA_DIR.mkdir(exist_ok=True)
FEEDBACK_DIR = DATA_DIR / "feedback"
FEEDBACK_DIR.mkdir(exist_ok=True)

# ─── Apify Configuration ──────────────────────────────────────────────────────
# YouTube scraper actor on Apify
APIFY_YT_ACTOR = os.getenv("APIFY_YT_ACTOR", "streamers/youtube-scraper")

# ─── NSE Configuration ────────────────────────────────────────────────────────
NSE_BASE_URL = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/market-data/bulk-block-deals",
}

# ─── Indian Trading YouTube Channels ──────────────────────────────────────────
# Curated list of popular Indian trading/finance YouTube channels
INDIAN_TRADING_CHANNELS = [
    "CA Rachana Phadke Ranade",
    "Pranjal Kamra",
    "Akshat Shrivastava",
    "Labour Law Advisor",
    "P R Sundar",
    "Trading Chanakya",
    "Power of Stocks",
    "Vivek Bajaj",
    "Elearn Markets",
    "Market Guru",
    "Nitin Bhatia",
    "Asset Yogi",
    "Pushkar Raj Thakur",
    "Groww",
    "Zerodha",
    "Angel One",
    "Motilal Oswal",
    "ICICI Direct",
    "Trade Brains",
    "MarketFeed",
    "StockEdge",
    "Fin Baba",
    "Trading with Vivek",
    "Booming Bulls",
    "Stock Market Telugu",
    "Trader Raghav",
    "Subhasish Pani",
    "Abhishek Kar",
    "Share Market Hindi",
    "Stock Pathshala",
]

# ─── Chunking Configuration ───────────────────────────────────────────────────
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks
MAX_CHUNKS_PER_VIDEO = 20

# ─── RAG Configuration ────────────────────────────────────────────────────────
TOP_K_RESULTS = 5  # number of chunks to retrieve per query
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def validate_config() -> list[str]:
    """Validate that required configuration is present. Returns list of errors."""
    errors = []
    if not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is not set. Get one from https://openrouter.ai/settings/keys")
    if not APIFY_API_TOKEN:
        errors.append("APIFY_API_TOKEN is not set. Get one from https://console.apify.com/account/integrations")
    return errors
