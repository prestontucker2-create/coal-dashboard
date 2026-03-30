"""
Sentiment domain fetcher.

Aggregates coal-related news headlines from Google News RSS and
optionally NewsAPI to feed sentiment analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

# Google News RSS search URLs
GOOGLE_NEWS_RSS_URLS = [
    (
        "https://news.google.com/rss/search?"
        "q=coal+mining+energy+price&hl=en-US&gl=US&ceid=US:en"
    ),
    (
        "https://news.google.com/rss/search?"
        "q=%22Peabody+Energy%22+OR+%22coal+stocks%22&hl=en-US&gl=US&ceid=US:en"
    ),
]

# NewsAPI endpoint
NEWSAPI_URL = "https://newsapi.org/v2/everything"


class SentimentFetcher(BaseFetcher):
    """Fetch coal-related news headlines from RSS and news APIs."""

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #
    async def fetch(self, **kwargs) -> dict[str, Any]:
        headlines: list[dict] = []

        # --- Google News RSS ---
        rss_headlines = await self._fetch_google_news_rss()
        headlines.extend(rss_headlines)

        # --- NewsAPI (if key available) ---
        api_keys = self.config.get("api_keys")
        newsapi_key = getattr(api_keys, "newsapi", "") if api_keys else ""
        if newsapi_key:
            newsapi_headlines = await self._fetch_newsapi(newsapi_key)
            headlines.extend(newsapi_headlines)
        else:
            logger.info("No NewsAPI key configured -- skipping NewsAPI fetch")

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique: list[dict] = []
        for h in headlines:
            url = h.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            unique.append(h)

        logger.info(
            "SentimentFetcher complete: %d headlines (%d unique)",
            len(headlines),
            len(unique),
        )
        return {"headlines": unique}

    # ------------------------------------------------------------------ #
    #  Google News RSS
    # ------------------------------------------------------------------ #
    async def _fetch_google_news_rss(self) -> list[dict]:
        """Parse Google News RSS feeds for coal-related headlines."""
        try:
            import feedparser
        except ImportError:
            logger.warning(
                "feedparser not installed -- skipping Google News RSS. "
                "Install with: pip install feedparser"
            )
            return []

        all_headlines: list[dict] = []

        for rss_url in GOOGLE_NEWS_RSS_URLS:
            try:
                resp = await self.fetch_with_retry(rss_url, timeout=15.0)
                feed = feedparser.parse(resp.text)

                for entry in feed.entries:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    # Extract source name from Google News title format:
                    # "Headline text - Source Name"
                    source_name = "Google News"
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        if len(parts) == 2:
                            title = parts[0].strip()
                            source_name = parts[1].strip()

                    # Parse published date
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published_at = datetime(
                                *entry.published_parsed[:6],
                                tzinfo=timezone.utc,
                            ).isoformat()
                        except Exception:
                            pass
                    if not published_at:
                        published_at = datetime.now(timezone.utc).isoformat()

                    all_headlines.append({
                        "title": title,
                        "url": entry.get("link", ""),
                        "source_name": source_name,
                        "published_at": published_at,
                    })

                logger.info(
                    "Google News RSS: %d entries from %s",
                    len(feed.entries),
                    rss_url[:80],
                )

            except Exception as exc:
                logger.warning("Google News RSS fetch failed for %s: %s", rss_url[:80], exc)

        return all_headlines

    # ------------------------------------------------------------------ #
    #  NewsAPI
    # ------------------------------------------------------------------ #
    async def _fetch_newsapi(self, api_key: str) -> list[dict]:
        """Fetch headlines from NewsAPI."""
        params = {
            "q": "coal energy mining",
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 20,
            "apiKey": api_key,
        }

        try:
            resp = await self.fetch_with_retry(NEWSAPI_URL, params=params, timeout=15.0)
            data = resp.json()

            articles = data.get("articles", [])
            headlines: list[dict] = []

            for article in articles:
                title = (article.get("title") or "").strip()
                if not title:
                    continue

                source_info = article.get("source", {})
                source_name = source_info.get("name", "NewsAPI") if isinstance(source_info, dict) else "NewsAPI"

                published_at = article.get("publishedAt")
                if not published_at:
                    published_at = datetime.now(timezone.utc).isoformat()

                headlines.append({
                    "title": title,
                    "url": article.get("url", ""),
                    "source_name": source_name,
                    "published_at": published_at,
                })

            logger.info("NewsAPI: retrieved %d articles", len(headlines))
            return headlines

        except Exception as exc:
            logger.error("NewsAPI fetch failed: %s", exc)
            return []
