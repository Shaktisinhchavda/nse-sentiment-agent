"""
Data Pipeline — orchestrates the full data ingestion flow.
Fetches NSE deals, YouTube videos, transcripts, sentiment, and indexes into vector store.
"""

import json
import logging
import time
from datetime import datetime
from src.config import DATA_DIR
from src.data.nse_deals import NSEDealsFetcher, fetch_deals_with_jugaad_fallback
from src.data.youtube_scraper import YouTubeScraper
from src.data.transcript_fetcher import TranscriptFetcher
from src.data.sentiment_analyzer import SentimentAnalyzer
from src.rag.chunker import chunk_transcript, chunk_sentiment_data, chunk_deals
from src.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DataPipeline:
    """Orchestrate the full data ingestion pipeline."""

    def __init__(self):
        self.vector_store = VectorStore()

    def run(self, max_videos: int = 100, skip_youtube: bool = False, skip_nse: bool = False) -> dict:
        """
        Run the full data pipeline.

        Args:
            max_videos: Maximum YouTube videos to fetch
            skip_youtube: Skip YouTube scraping (use cached data)
            skip_nse: Skip NSE deal fetching

        Returns:
            Summary statistics dict
        """
        stats = {
            "start_time": datetime.now().isoformat(),
            "nse_deals": 0,
            "youtube_videos": 0,
            "transcripts": 0,
            "sentiments": 0,
            "chunks_indexed": 0,
        }

        # Step 1: Fetch NSE Bulk & Block Deals
        if not skip_nse:
            logger.info("=" * 60)
            logger.info("STEP 1: Fetching NSE Bulk & Block Deals")
            logger.info("=" * 60)
            try:
                fetcher = NSEDealsFetcher()
                deals = fetcher.fetch_all_deals()
                deal_docs = fetcher.format_deals_for_rag(deals)
                deal_chunks = chunk_deals(deal_docs)
                added = self.vector_store.add_documents(deal_chunks)
                stats["nse_deals"] = deals.get("total_count", 0)
                stats["chunks_indexed"] += added
                logger.info("NSE deals indexed: %d documents", added)
            except Exception as e:
                logger.error("NSE deal fetch failed: %s", e)

        # Step 2: Fetch YouTube Videos
        if not skip_youtube:
            logger.info("=" * 60)
            logger.info("STEP 2: Fetching YouTube Trading Videos")
            logger.info("=" * 60)
            try:
                # Try cache first
                cached = YouTubeScraper.load_cache()
                if cached:
                    videos = cached
                    logger.info("Using cached videos: %d", len(videos))
                else:
                    scraper = YouTubeScraper()
                    videos = scraper.search_trading_videos(max_videos=max_videos)

                stats["youtube_videos"] = len(videos)

                # Step 3: Fetch Transcripts
                logger.info("=" * 60)
                logger.info("STEP 3: Fetching Video Transcripts")
                logger.info("=" * 60)
                tf = TranscriptFetcher()
                videos_with_transcripts = tf.batch_fetch(videos)
                with_t = sum(1 for v in videos_with_transcripts if v.get("transcript"))
                stats["transcripts"] = with_t

                # Step 4: Chunk transcripts and index
                logger.info("=" * 60)
                logger.info("STEP 4: Chunking and Indexing Transcripts")
                logger.info("=" * 60)
                all_chunks = []
                for video in videos_with_transcripts:
                    chunks = chunk_transcript(video)
                    all_chunks.extend(chunks)

                if all_chunks:
                    added = self.vector_store.add_documents(all_chunks)
                    stats["chunks_indexed"] += added

                # Step 5: Sentiment Analysis
                logger.info("=" * 60)
                logger.info("STEP 5: Analyzing Sentiment")
                logger.info("=" * 60)
                analyzer = SentimentAnalyzer()
                sentiments = analyzer.batch_analyze(videos_with_transcripts)
                stats["sentiments"] = len(sentiments)

                # Index sentiment data
                sentiment_chunks = chunk_sentiment_data(sentiments)
                if sentiment_chunks:
                    added = self.vector_store.add_documents(sentiment_chunks)
                    stats["chunks_indexed"] += added

                # Save sentiments to disk
                self._save_sentiments(sentiments)

            except Exception as e:
                logger.error("YouTube pipeline failed: %s", e)
                import traceback
                traceback.print_exc()

        stats["end_time"] = datetime.now().isoformat()
        stats["vector_store"] = self.vector_store.stats()

        # Save stats
        stats_file = DATA_DIR / "pipeline_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, default=str)

        self._print_summary(stats)
        return stats

    def _save_sentiments(self, sentiments: list[dict]):
        """Save sentiment results to disk."""
        path = DATA_DIR / "sentiments.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sentiments, f, indent=2, default=str)
            logger.info("Saved %d sentiments to %s", len(sentiments), path)
        except Exception as e:
            logger.warning("Failed to save sentiments: %s", e)

    def _print_summary(self, stats: dict):
        """Print a summary of the pipeline run."""
        print("\n" + "=" * 60)
        print("  DATA PIPELINE SUMMARY")
        print("=" * 60)
        print(f"  NSE Deals fetched:      {stats['nse_deals']}")
        print(f"  YouTube videos:         {stats['youtube_videos']}")
        print(f"  Transcripts obtained:   {stats['transcripts']}")
        print(f"  Sentiment entries:      {stats['sentiments']}")
        print(f"  Chunks indexed:         {stats['chunks_indexed']}")
        vs = stats.get("vector_store", {})
        print(f"  Total docs in store:    {vs.get('total_documents', 'N/A')}")
        print("=" * 60 + "\n")
