"""
NSE Bulk & Block Deals Fetcher.

Fetches bulk and block deal data from NSE India for the last 24 hours.
Uses direct HTTP requests with proper session management to handle NSE's anti-bot measures.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
import pandas as pd

from src.config import NSE_BASE_URL, NSE_HEADERS, DATA_DIR

logger = logging.getLogger(__name__)


class NSEDealsFetcher:
    """Fetch Bulk & Block deals from NSE India."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(NSE_HEADERS)
        self._cookies_set = False

    def _init_session(self):
        """Initialize session with NSE cookies (required to bypass anti-bot)."""
        if self._cookies_set:
            return
        try:
            logger.info("Initializing NSE session (fetching cookies)...")
            resp = self.session.get(NSE_BASE_URL, timeout=10)
            resp.raise_for_status()
            self._cookies_set = True
            logger.info("NSE session initialized successfully")
            time.sleep(1)  # Be respectful
        except Exception as e:
            logger.warning("Failed to initialize NSE session: %s", e)

    def fetch_bulk_deals(self) -> list[dict]:
        """Fetch bulk deals from NSE for today."""
        self._init_session()
        url = f"{NSE_BASE_URL}/api/snapshot-capital-market-largedeal"
        try:
            logger.info("Fetching bulk deals from NSE...")
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            # NSE returns data in different formats depending on the endpoint
            deals = []
            if isinstance(data, dict):
                # Try common keys
                for key in ["BULK_DEALS", "data", "bulkDeals", "bulk"]:
                    if key in data:
                        raw_deals = data[key]
                        if isinstance(raw_deals, list):
                            deals = raw_deals
                            break
                if not deals and "data" not in data:
                    # The whole response might be the data container
                    deals = [data] if "symbol" in data else []
            elif isinstance(data, list):
                deals = data

            logger.info("Fetched %d bulk deal records from NSE", len(deals))
            return deals

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 401:
                logger.warning("NSE session expired, refreshing cookies...")
                self._cookies_set = False
                self._init_session()
                return self.fetch_bulk_deals()
            logger.error("HTTP error fetching bulk deals: %s", e)
            return []
        except Exception as e:
            logger.error("Error fetching bulk deals: %s", e)
            return []

    def fetch_block_deals(self) -> list[dict]:
        """Fetch block deals from NSE for today."""
        self._init_session()
        url = f"{NSE_BASE_URL}/api/block-deal"
        try:
            logger.info("Fetching block deals from NSE...")
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            deals = []
            if isinstance(data, dict):
                for key in ["data", "BLOCK_DEALS", "blockDeals", "block"]:
                    if key in data:
                        raw_deals = data[key]
                        if isinstance(raw_deals, list):
                            deals = raw_deals
                            break
            elif isinstance(data, list):
                deals = data

            logger.info("Fetched %d block deal records from NSE", len(deals))
            return deals

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 401:
                logger.warning("NSE session expired, refreshing cookies...")
                self._cookies_set = False
                self._init_session()
                return self.fetch_block_deals()
            logger.error("HTTP error fetching block deals: %s", e)
            return []
        except Exception as e:
            logger.error("Error fetching block deals: %s", e)
            return []

    def fetch_all_deals(self) -> dict:
        """Fetch both bulk and block deals. Returns combined result."""
        bulk = self.fetch_bulk_deals()
        time.sleep(1)  # Rate limiting
        block = self.fetch_block_deals()

        result = {
            "bulk_deals": bulk,
            "block_deals": block,
            "fetch_time": datetime.now().isoformat(),
            "total_count": len(bulk) + len(block),
        }

        # Save to disk for caching
        cache_path = DATA_DIR / "nse_deals.json"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            logger.info("Cached NSE deals to %s", cache_path)
        except Exception as e:
            logger.warning("Failed to cache deals: %s", e)

        return result

    def format_deals_for_rag(self, deals_data: dict) -> list[dict]:
        """Format deals into documents suitable for RAG indexing."""
        documents = []
        now = datetime.now()

        for deal_type in ["bulk_deals", "block_deals"]:
            for deal in deals_data.get(deal_type, []):
                # Normalize field names (NSE uses varying keys)
                symbol = (
                    deal.get("symbol", "")
                    or deal.get("SYMBOL", "")
                    or deal.get("scrip", "")
                    or deal.get("SCRIP", "")
                    or "UNKNOWN"
                )
                client_name = (
                    deal.get("clientName", "")
                    or deal.get("CLIENT_NAME", "")
                    or deal.get("client", "")
                    or "Unknown"
                )
                trade_type = (
                    deal.get("buySell", "")
                    or deal.get("BUY_SELL", "")
                    or deal.get("tradeType", "")
                    or ""
                )
                quantity = (
                    deal.get("quantity", "")
                    or deal.get("QUANTITY", "")
                    or deal.get("qty", "")
                    or ""
                )
                price = (
                    deal.get("tradePrice", "")
                    or deal.get("TRADE_PRICE", "")
                    or deal.get("price", "")
                    or ""
                )
                deal_date = (
                    deal.get("dealDate", "")
                    or deal.get("DEAL_DATE", "")
                    or deal.get("date", "")
                    or now.strftime("%d-%b-%Y")
                )

                doc_text = (
                    f"[NSE {deal_type.replace('_', ' ').title()}] "
                    f"Symbol: {symbol} | "
                    f"Client: {client_name} | "
                    f"Trade: {trade_type} | "
                    f"Quantity: {quantity} | "
                    f"Price: ₹{price} | "
                    f"Date: {deal_date}"
                )

                documents.append({
                    "text": doc_text,
                    "metadata": {
                        "source": "NSE",
                        "type": deal_type,
                        "symbol": symbol.upper(),
                        "client": client_name,
                        "trade_type": trade_type,
                        "quantity": str(quantity),
                        "price": str(price),
                        "date": deal_date,
                        "fetch_time": deals_data.get("fetch_time", ""),
                    },
                })

        logger.info("Formatted %d deal documents for RAG", len(documents))
        return documents


def fetch_deals_with_jugaad_fallback() -> dict:
    """Try NSE direct API first, fall back to jugaad-data if needed."""
    fetcher = NSEDealsFetcher()
    result = fetcher.fetch_all_deals()

    if result["total_count"] == 0:
        logger.warning("No deals from NSE direct API, trying jugaad-data fallback...")
        try:
            from jugaad_data.nse import NSELive
            nse = NSELive()

            # jugaad-data may not have bulk/block deals directly,
            # but we can get market data
            try:
                market_status = nse.market_status()
                logger.info("Market status from jugaad-data: %s", market_status)
            except Exception:
                pass

            # Try to get some trading data
            try:
                top_gainers = nse.trade_info()
                if top_gainers:
                    result["market_info"] = top_gainers
                    logger.info("Got market trade info from jugaad-data")
            except Exception:
                pass

        except ImportError:
            logger.warning("jugaad-data not installed, skipping fallback")
        except Exception as e:
            logger.warning("jugaad-data fallback failed: %s", e)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = NSEDealsFetcher()
    deals = fetcher.fetch_all_deals()
    print(f"\nTotal deals fetched: {deals['total_count']}")
    print(f"Bulk deals: {len(deals['bulk_deals'])}")
    print(f"Block deals: {len(deals['block_deals'])}")

    docs = fetcher.format_deals_for_rag(deals)
    for doc in docs[:5]:
        print(f"\n{doc['text']}")
