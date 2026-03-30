"""
Weather domain processor.

Normalises raw ENSO and degree day data into storage-ready records
for the enso_status and degree_days tables.
"""

from __future__ import annotations

import logging
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)


class WeatherProcessor(BaseProcessor):
    """Process ENSO and HDD/CDD data into storage records."""

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        enso_rows = raw_data.get("enso") or []
        degree_day_rows = raw_data.get("degree_days") or []

        records.extend(self._process_enso(enso_rows))
        records.extend(self._process_degree_days(degree_day_rows))

        logger.info(
            "WeatherProcessor produced %d total records "
            "(%d ENSO, %d degree_days)",
            len(records),
            len([r for r in records if r["_table"] == "enso_status"]),
            len([r for r in records if r["_table"] == "degree_days"]),
        )
        return records

    # ------------------------------------------------------------------ #
    #  ENSO processing
    # ------------------------------------------------------------------ #
    def _process_enso(self, rows: list[dict]) -> list[dict[str, Any]]:
        """Validate and normalise ENSO/ONI records."""
        records: list[dict[str, Any]] = []

        for row in rows:
            try:
                oni_value = row.get("oni_value")
                if oni_value is None:
                    continue

                oni_value = float(oni_value)
                phase = row.get("phase", "")
                period_date = row.get("period_date", "")

                if not period_date:
                    continue

                # Re-classify phase if needed (in case source data is raw)
                if not phase:
                    if oni_value >= 0.5:
                        phase = "El Nino"
                    elif oni_value <= -0.5:
                        phase = "La Nina"
                    else:
                        phase = "Neutral"

                records.append({
                    "_table": "enso_status",
                    "oni_value": round(oni_value, 2),
                    "phase": phase,
                    "period_date": self._normalize_date(period_date),
                    "source": "noaa",
                })
            except Exception as exc:
                logger.debug("Skipping ENSO row: %s -- %s", row, exc)

        return records

    # ------------------------------------------------------------------ #
    #  Degree days processing
    # ------------------------------------------------------------------ #
    def _process_degree_days(self, rows: list[dict]) -> list[dict[str, Any]]:
        """Validate and normalise degree day records."""
        records: list[dict[str, Any]] = []

        for row in rows:
            try:
                region = row.get("region", "US")
                period_date = row.get("period_date", "")
                if not period_date:
                    continue

                hdd = row.get("hdd")
                cdd = row.get("cdd")

                # At least one of HDD or CDD must be present
                if hdd is None and cdd is None:
                    continue

                hdd_val = float(hdd) if hdd is not None else None
                cdd_val = float(cdd) if cdd is not None else None
                deviation = row.get("deviation_from_normal")
                deviation_val = float(deviation) if deviation is not None else None

                records.append({
                    "_table": "degree_days",
                    "region": region,
                    "hdd": round(hdd_val, 1) if hdd_val is not None else None,
                    "cdd": round(cdd_val, 1) if cdd_val is not None else None,
                    "deviation_from_normal": (
                        round(deviation_val, 1) if deviation_val is not None else None
                    ),
                    "period_date": self._normalize_date(period_date),
                    "source": "noaa",
                })
            except Exception as exc:
                logger.debug("Skipping degree day row: %s -- %s", row, exc)

        return records

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """Ensure date is in YYYY-MM-DD format."""
        date_str = date_str.strip()
        if len(date_str) == 7:  # YYYY-MM
            return f"{date_str}-01"
        if len(date_str) >= 10:
            return date_str[:10]
        return date_str
