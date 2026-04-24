"""
YouTube Transcript Fetcher.
Fetches transcripts from YouTube videos using youtube-transcript-api (primary)
and Apify (fallback).
"""

import logging
import time
from typing import Optional
from src.config import APIFY_API_TOKEN

logger = logging.getLogger(__name__)


class TranscriptFetcher:
    """Fetch transcripts from YouTube videos."""

    def __init__(self):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self._yt_api = YouTubeTranscriptApi()
            self._has_yt_api = True
        except ImportError:
            logger.warning("youtube-transcript-api not installed")
            self._yt_api = None
            self._has_yt_api = False

    def get_transcript(self, video_id: str, video_url: str = "") -> Optional[dict]:
        """Get transcript for a YouTube video. Returns dict with text/segments or None."""
        if self._has_yt_api:
            result = self._fetch_via_yt_api(video_id)
            if result:
                return result
        # Temporarily disabling Apify fallback for transcripts to avoid 429 Too Many Requests errors
        # on the free tier. If yt-api fails, we just skip the video.
        return None

    def _fetch_via_yt_api(self, video_id: str) -> Optional[dict]:
        try:
            transcript_list = self._yt_api.list(video_id)
            transcript = None
            for lang in ["en", "hi"]:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue
            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript(["en", "hi"])
                except Exception:
                    available = list(transcript_list)
                    transcript = available[0] if available else None
            if not transcript:
                return None
            fetched = transcript.fetch()
            if hasattr(fetched, "to_raw_data"):
                segments = fetched.to_raw_data()
            else:
                segments = list(fetched)
                
            full_text = " ".join(s.get("text", "") for s in segments)
            timestamped = [{"text": s.get("text",""), "start": s.get("start",0), "duration": s.get("duration",0)} for s in segments]
            return {"text": full_text, "segments": timestamped, "language": getattr(transcript, 'language_code', 'en'), "source": "youtube-transcript-api"}
        except Exception as e:
            error_msg = str(e)
            if "Subtitles are disabled" in error_msg:
                logger.debug("Subtitles disabled for %s", video_id)
            elif "No transcripts were found" in error_msg:
                logger.debug("No transcripts found for %s", video_id)
            else:
                logger.warning("yt-api error for %s: %s", video_id, error_msg[:100])
            return None

    def batch_fetch(self, videos: list[dict], delay: float = 0.5, max_failures: int = 100) -> list[dict]:
        """Fetch transcripts for a batch of videos, using Apify for failures in one bulk call."""
        results = []
        fails = 0
        failed_videos = []

        # Pass 1: Try youtube-transcript-api
        for i, video in enumerate(videos):
            vid = video.get("id", "")
            if not vid:
                continue
            logger.info("Transcript %d/%d: %s", i+1, len(videos), video.get("title","")[:60])
            
            transcript = None
            if self._has_yt_api:
                transcript = self._fetch_via_yt_api(vid)
                
            enriched = dict(video)
            if transcript:
                enriched["transcript"] = transcript
                fails = 0
                logger.info("  ✓ Got transcript via yt-api (%d chars)", len(transcript["text"]))
            else:
                fails += 1
                logger.info("  ✗ No transcript via yt-api")
                enriched["transcript"] = None
                if APIFY_API_TOKEN:
                    failed_videos.append(enriched)

            results.append(enriched)
            
            if fails >= max_failures:
                logger.warning("Stopping yt-api after %d consecutive failures", max_failures)
                for r in videos[i+1:]:
                    rc = dict(r); rc["transcript"] = None
                    if APIFY_API_TOKEN:
                        failed_videos.append(rc)
                    results.append(rc)
                break
                
            time.sleep(delay)

        # Pass 2: Bulk Apify fallback
        if failed_videos and APIFY_API_TOKEN:
            logger.info("Running bulk Apify fallback for %d videos without transcripts...", len(failed_videos))
            urls = [v.get("url", f"https://www.youtube.com/watch?v={v.get('id')}") for v in failed_videos]
            
            apify_transcripts = self._batch_fetch_via_apify(urls)
            
            # Merge back
            if apify_transcripts:
                for r in results:
                    if r["transcript"] is None and r.get("id") in apify_transcripts:
                        r["transcript"] = apify_transcripts[r["id"]]
                        logger.info("  ✓ Recovered transcript via Apify: %s", r.get("title","")[:40])

        ok = sum(1 for r in results if r.get("transcript"))
        logger.info("Transcripts: %d/%d videos", ok, len(results))
        return results

    def _batch_fetch_via_apify(self, urls: list[str]) -> dict:
        """Fetch transcripts for multiple URLs in one Apify run to save credits/avoid 429s."""
        transcripts_by_id = {}
        try:
            from apify_client import ApifyClient
            from src.config import APIFY_YT_ACTOR
            client = ApifyClient(APIFY_API_TOKEN)
            
            # Run the actor with all URLs at once
            run_input = {
                "startUrls": [{"url": u} for u in urls],
                "downloadSubtitles": True,
                "downloadAutoGeneratedSubtitles": True,
                "maxResults": len(urls)
            }
            
            run = client.actor(APIFY_YT_ACTOR).call(
                run_input=run_input,
                timeout_secs=300, # Allow 5 mins for batch
            )
            
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                video_url = item.get("url", "")
                
                # Extract ID from url
                import re
                match = re.search(r'(?:v=|/v/|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})', video_url)
                if not match:
                    continue
                video_id = match.group(1)
                
                txt = item.get("text") or item.get("subtitles") or item.get("transcript") or ""
                if isinstance(txt, list):
                    segs = [{"text": s.get("text","") if isinstance(s,dict) else str(s), "start": s.get("start",0) if isinstance(s,dict) else 0, "duration": 0} for s in txt]
                    txt = " ".join(s["text"] for s in segs)
                else:
                    segs = [{"text": txt, "start": 0, "duration": 0}]
                    
                if txt.strip():
                    transcripts_by_id[video_id] = {
                        "text": txt,
                        "segments": segs,
                        "language": "en",
                        "source": "apify_batch"
                    }
                    
        except Exception as e:
            logger.error("Apify batch transcript fetch failed: %s", e)
            
        return transcripts_by_id
