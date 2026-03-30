"""
Sentiment domain processor.

Performs keyword-based sentiment scoring on news headlines, tags mentioned
tickers and relevance categories (coal_price, policy, company, supply, demand).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Sentiment keyword dictionaries
# ------------------------------------------------------------------ #
BULLISH_WORDS = {
    "surge", "rally", "demand", "shortage", "bullish", "upgrade",
    "profit", "beat", "soar", "boom", "tight", "deficit",
    "gain", "rise", "strong", "record", "outperform", "buy",
    "growth", "expand", "higher", "up", "jump", "spike",
}

BEARISH_WORDS = {
    "decline", "ban", "transition", "bearish", "downgrade",
    "closure", "slump", "miss", "crash", "phase-out", "oversupply",
    "drop", "fall", "weak", "loss", "sell", "cut", "lower",
    "down", "plunge", "shut", "layoff", "bankrupt", "regulatory",
}

# ------------------------------------------------------------------ #
#  Ticker detection
# ------------------------------------------------------------------ #
COAL_TICKERS = {
    "BTU": "Peabody Energy",
    "ARCH": "Arch Resources",
    "ARLP": "Alliance Resource Partners",
    "CEIX": "CONSOL Energy",
    "HCC": "Warrior Met Coal",
    "AMR": "Alpha Metallurgical Resources",
    "NRP": "Natural Resource Partners",
    "METC": "Ramaco Resources",
    "NC": "NACCO Industries",
    "SXC": "SunCoke Energy",
    "CTRA": "Coterra Energy",
}

COAL_COMPANY_NAMES = {
    "peabody": "BTU",
    "arch resources": "ARCH",
    "alliance resource": "ARLP",
    "consol energy": "CEIX",
    "consol": "CEIX",
    "warrior met": "HCC",
    "warrior coal": "HCC",
    "alpha metallurgical": "AMR",
    "ramaco": "METC",
    "nacco": "NC",
    "suncoke": "SXC",
}

# ------------------------------------------------------------------ #
#  Relevance tag keywords
# ------------------------------------------------------------------ #
RELEVANCE_KEYWORDS = {
    "coal_price": {"price", "benchmark", "newcastle", "pricing", "cost", "rate", "tariff"},
    "policy": {"regulation", "policy", "epa", "ban", "legislation", "bill", "act",
               "government", "regulatory", "permit", "emission", "carbon"},
    "company": {"earnings", "revenue", "profit", "dividend", "stock", "shares",
                "acquisition", "merger", "ceo", "board", "quarterly"},
    "supply": {"production", "mine", "mining", "output", "export", "shipment",
               "inventory", "stockpile", "supply"},
    "demand": {"demand", "consumption", "generation", "electricity", "power",
               "utility", "grid", "heating", "industrial"},
}


class SentimentProcessor(BaseProcessor):
    """Score headlines for sentiment and tag with tickers and relevance."""

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        headlines = raw_data.get("headlines") or []

        for headline in headlines:
            try:
                rec = self._process_headline(headline)
                if rec is not None:
                    records.append(rec)
            except Exception as exc:
                logger.debug("Skipping headline: %s -- %s", headline, exc)

        logger.info("SentimentProcessor produced %d records", len(records))
        return records

    # ------------------------------------------------------------------ #
    #  Headline-level processing
    # ------------------------------------------------------------------ #
    def _process_headline(self, headline: dict) -> dict[str, Any] | None:
        """Process a single headline into a storage record."""
        title = headline.get("title", "").strip()
        if not title:
            return None

        # Compute sentiment score
        sentiment_score = self._compute_sentiment(title)

        # Detect tickers mentioned
        tickers_mentioned = self._detect_tickers(title)

        # Determine relevance tags
        relevance_tag = self._determine_relevance(title)

        return {
            "_table": "news_headlines",
            "title": title,
            "url": headline.get("url", ""),
            "source_name": headline.get("source_name", "unknown"),
            "published_at": headline.get("published_at", ""),
            "sentiment_score": round(sentiment_score, 3),
            "relevance_tag": relevance_tag,
            "tickers_mentioned": ",".join(tickers_mentioned) if tickers_mentioned else None,
        }

    # ------------------------------------------------------------------ #
    #  Sentiment scoring
    # ------------------------------------------------------------------ #
    def _compute_sentiment(self, title: str) -> float:
        """Compute a simple keyword-based sentiment score from -1.0 to 1.0.

        The score is calculated as:
            (bullish_count - bearish_count) / max(total_matches, 1)
        Then clamped to [-1.0, 1.0].
        """
        words = set(re.findall(r'[a-z]+(?:-[a-z]+)*', title.lower()))

        bullish_count = len(words & BULLISH_WORDS)
        bearish_count = len(words & BEARISH_WORDS)

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        score = (bullish_count - bearish_count) / total
        return max(-1.0, min(1.0, score))

    # ------------------------------------------------------------------ #
    #  Ticker detection
    # ------------------------------------------------------------------ #
    def _detect_tickers(self, title: str) -> list[str]:
        """Detect coal company tickers mentioned in the headline.

        Matches against:
        1. Exact ticker symbols (uppercase, word-bounded)
        2. Company name substrings (case-insensitive)
        """
        found: set[str] = set()
        title_upper = title.upper()
        title_lower = title.lower()

        # Check for ticker symbols
        words_upper = set(re.findall(r'\b[A-Z]{2,5}\b', title_upper))
        for ticker in COAL_TICKERS:
            if ticker in words_upper:
                found.add(ticker)

        # Check for company names
        for name_lower, ticker in COAL_COMPANY_NAMES.items():
            if name_lower in title_lower:
                found.add(ticker)

        return sorted(found)

    # ------------------------------------------------------------------ #
    #  Relevance tagging
    # ------------------------------------------------------------------ #
    def _determine_relevance(self, title: str) -> str:
        """Determine the primary relevance tag for a headline.

        Returns the tag with the most keyword matches. Defaults to
        'general' if no specific category matches.
        """
        title_lower = title.lower()
        words = set(re.findall(r'[a-z]+', title_lower))

        best_tag = "general"
        best_count = 0

        for tag, keywords in RELEVANCE_KEYWORDS.items():
            count = len(words & keywords)
            if count > best_count:
                best_count = count
                best_tag = tag

        return best_tag
