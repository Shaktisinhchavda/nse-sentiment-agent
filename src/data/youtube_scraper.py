"""
YouTube Video Scraper using Apify.

Fetches recent videos from Indian trading/finance YouTube channels
using the Apify YouTube Scraper actor.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

from src.config import APIFY_API_TOKEN, APIFY_YT_ACTOR, INDIAN_TRADING_CHANNELS, DATA_DIR

logger = logging.getLogger(__name__)


class YouTubeScraper:
    """Scrape YouTube videos from Indian trading channels using Apify."""

    def __init__(self, api_token: str = None):
        self.api_token = api_token or APIFY_API_TOKEN
        if not self.api_token:
            raise ValueError(
                "APIFY_API_TOKEN is required. "
                "Get one from https://console.apify.com/account/integrations"
            )

        try:
            from apify_client import ApifyClient
            self.client = ApifyClient(self.api_token)
        except ImportError:
            raise ImportError("apify-client is required: pip install apify-client")

    def search_trading_videos(self, max_videos: int = 100) -> list[dict]:
        """
        Search for recent Indian trading videos on YouTube.

        Uses search queries related to Indian stock market trading
        to find recent content from trading creators.

        Args:
            max_videos: Maximum number of videos to fetch (default: 100)

        Returns:
            List of video metadata dictionaries
        """
        logger.info("Searching for %d Indian trading YouTube videos via Apify...", max_videos)

        # Build search queries targeting Indian stock market content
        search_queries = [
            "NSE stock market analysis today India",
            "Indian stock market trading today",
            "NIFTY analysis today",
            "SENSEX market update today",
            "NSE stock picks today India",
            "Indian share market news today",
            "RELIANCE HDFC TATA stock analysis",
            "Indian stock market live trading",
            "NSE intraday trading today",
            "FII DII data today India market",
        ]

        all_videos = []
        videos_per_query = max(10, max_videos // len(search_queries))

        for query in search_queries:
            if len(all_videos) >= max_videos:
                break

            try:
                videos = self._run_youtube_search(query, videos_per_query)
                all_videos.extend(videos)
                logger.info(
                    "Query '%s' returned %d videos (total: %d)",
                    query, len(videos), len(all_videos)
                )
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.warning("Failed to search for '%s': %s", query, e)
                continue

        # Deduplicate by video ID
        seen_ids = set()
        unique_videos = []
        for video in all_videos:
            vid = video.get("id") or video.get("url", "")
            if vid and vid not in seen_ids:
                seen_ids.add(vid)
                unique_videos.append(video)

        # Trim to max
        unique_videos = unique_videos[:max_videos]
        logger.info("Total unique videos collected: %d", len(unique_videos))

        # Cache results
        self._save_cache(unique_videos)

        return unique_videos

    def _run_youtube_search(self, query: str, max_results: int = 15) -> list[dict]:
        """Run a single YouTube search via Apify actor."""
        run_input = {
            "searchKeywords": query,
            "maxResults": max_results,
            "sortBy": "date",  # Most recent first
            "uploadDate": "today",  # Last 24 hours
            "language": "en",
            "maxResultsShorts": 0,  # Skip shorts
        }

        try:
            # Try the youtube-scraper actor
            run = self.client.actor(APIFY_YT_ACTOR).call(
                run_input=run_input,
                timeout_secs=120,
            )

            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                video = self._normalize_video(item)
                if video:
                    items.append(video)

            return items

        except Exception as e:
            logger.warning("Apify actor '%s' failed: %s", APIFY_YT_ACTOR, e)

            # Fallback: try alternative actor
            try:
                return self._fallback_search(query, max_results)
            except Exception as e2:
                logger.error("Fallback search also failed: %s", e2)
                return []

    def _fallback_search(self, query: str, max_results: int = 15) -> list[dict]:
        """Fallback YouTube search using a different Apify actor."""
        run_input = {
            "searchTerms": [query],
            "maxResults": max_results,
            "sortBy": "upload_date",
        }

        try:
            run = self.client.actor("apify/youtube-scraper").call(
                run_input=run_input,
                timeout_secs=120,
            )

            items = []
            for item in self.client.dataset(run["defaultDatasetId"]).iterate_items():
                video = self._normalize_video(item)
                if video:
                    items.append(video)

            return items
        except Exception as e:
            logger.error("Fallback actor also failed: %s", e)
            return []

    def _normalize_video(self, raw: dict) -> Optional[dict]:
        """Normalize video data from various Apify actor formats."""
        video_id = (
            raw.get("id")
            or raw.get("videoId")
            or self._extract_id_from_url(raw.get("url", ""))
        )
        if not video_id:
            return None

        title = raw.get("title") or raw.get("name") or ""
        channel = (
            raw.get("channelName")
            or raw.get("channel")
            or raw.get("channelTitle")
            or raw.get("author", {}).get("name", "")
            if isinstance(raw.get("author"), dict) else
            raw.get("channelName", "Unknown Channel")
        )
        url = raw.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        published = (
            raw.get("date")
            or raw.get("publishedAt")
            or raw.get("uploadDate")
            or ""
        )
        duration = raw.get("duration") or raw.get("lengthSeconds") or ""
        views = raw.get("viewCount") or raw.get("views") or 0
        description = raw.get("description") or raw.get("text") or ""

        return {
            "id": video_id,
            "title": title,
            "channel": channel,
            "url": url,
            "published": published,
            "duration": str(duration),
            "views": views,
            "description": description[:500],  # Truncate long descriptions
        }

    @staticmethod
    def _extract_id_from_url(url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        if not url:
            return None
        import re
        patterns = [
            r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'(?:embed/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _save_cache(self, videos: list[dict]):
        """Save fetched videos to a local cache file."""
        cache_path = DATA_DIR / "youtube_videos.json"
        try:
            cache_data = {
                "videos": videos,
                "count": len(videos),
                "fetch_time": datetime.now().isoformat(),
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, default=str)
            logger.info("Cached %d videos to %s", len(videos), cache_path)
        except Exception as e:
            logger.warning("Failed to cache videos: %s", e)

    @staticmethod
    def load_cache() -> Optional[list[dict]]:
        """Load videos from cache if recent (< 6 hours old)."""
        cache_path = DATA_DIR / "youtube_videos.json"
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            fetch_time = datetime.fromisoformat(data["fetch_time"])
            if datetime.now() - fetch_time > timedelta(hours=6):
                logger.info("Cache is stale (> 6 hours), will re-fetch")
                return None

            logger.info("Loaded %d videos from cache", data["count"])
            return data["videos"]
        except Exception as e:
            logger.warning("Failed to load cache: %s", e)
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = YouTubeScraper()
    videos = scraper.search_trading_videos(max_videos=10)
    print(f"\nFetched {len(videos)} videos:")
    for v in videos[:5]:
        print(f"  - [{v['channel']}] {v['title']}")
        print(f"    URL: {v['url']}")
