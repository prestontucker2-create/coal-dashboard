import logging
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)

# Map FRED series IDs to normalised lowercase slugs used throughout the dashboard
SERIES_SLUG_MAP = {
    "DEXUSAL": "audusd",
    "DTWEXBGS": "dxy",
    "DGS10": "us10y",
    "DHHNGSP": "henry_hub",
    "NAPMPI": "pmi_mfg",
}


class MacroProcessor(BaseProcessor):
    """Processes raw FRED observations into clean records for storage.

    Responsibilities:
    - Normalise FRED series IDs to lowercase dashboard slugs
    - Filter out missing / null values (FRED uses "." for missing data)
    - Convert string values to float
    """

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        indicators = raw_data.get("indicators", [])
        if not indicators:
            return []

        records: list[dict[str, Any]] = []
        skipped = 0

        for entry in indicators:
            raw_value = entry.get("value")

            # FRED represents missing data as the string "."
            if raw_value is None or str(raw_value).strip() == ".":
                skipped += 1
                continue

            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                skipped += 1
                logger.debug(f"Non-numeric value for {entry.get('indicator')}: {raw_value!r}")
                continue

            series_id = entry.get("indicator", "")
            slug = SERIES_SLUG_MAP.get(series_id, series_id.lower())

            records.append({
                "indicator": slug,
                "value": value,
                "timestamp": entry.get("timestamp"),
                "source": entry.get("source", "fred"),
            })

        logger.info(f"MacroProcessor: {len(records)} valid records, {skipped} skipped (missing/null)")
        return records
