"""
Demand domain processor.

Normalises raw EIA electricity generation rows into storage-ready records
for the power_generation table.
"""

from __future__ import annotations

import logging
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)

# EIA fuel type ID -> human-readable label
FUEL_TYPE_MAP = {
    "COL": "coal",
    "NG": "natural_gas",
    "NUC": "nuclear",
    "SUN": "solar",
    "WND": "wind",
    "ALL": "total",
    "PEL": "petroleum",
    "HYC": "hydro",
    "GEO": "geothermal",
    "BIO": "biomass",
    "OTH": "other",
}


class DemandProcessor(BaseProcessor):
    """Transform raw EIA generation data into normalised storage records."""

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        generation_rows = raw_data.get("generation") or []

        for row in generation_rows:
            try:
                rec = self._process_generation_row(row)
                if rec is not None:
                    records.append(rec)
            except Exception as exc:
                logger.debug("Skipping generation row: %s -- %s", row, exc)

        logger.info("DemandProcessor produced %d records", len(records))
        return records

    # ------------------------------------------------------------------ #
    #  Row-level processing
    # ------------------------------------------------------------------ #
    def _process_generation_row(self, row: dict) -> dict[str, Any] | None:
        """Convert a single EIA generation row to a storage record."""
        generation_raw = row.get("generation")
        if generation_raw is None:
            return None

        try:
            generation_mwh = float(generation_raw)
        except (ValueError, TypeError):
            return None

        # Extract fuel type
        fuel_id = (
            row.get("fueltypeid")
            or row.get("fuelTypeId")
            or row.get("fueltypeid", "")
        )
        fuel_type = FUEL_TYPE_MAP.get(str(fuel_id).upper(), str(fuel_id).lower())

        # Extract region -- EIA uses various field names
        region = self._extract_region(row)

        # Period handling
        period = row.get("period", "")
        period_type = self._infer_period_type(period)
        period_date = self._normalize_period_date(period)

        return {
            "_table": "power_generation",
            "region": region,
            "fuel_type": fuel_type,
            "generation_mwh": round(generation_mwh, 2),
            "period_type": period_type,
            "period_date": period_date,
            "source": "eia",
        }

    # ------------------------------------------------------------------ #
    #  Utility methods
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_region(row: dict) -> str:
        """Best-effort region extraction from an EIA row."""
        for key in (
            "statedescription", "stateDescription", "stateid",
            "stateId", "location",
        ):
            val = row.get(key)
            if val:
                return str(val)
        return "US"

    @staticmethod
    def _infer_period_type(period: str) -> str:
        """Return 'annual', 'quarterly', or 'monthly' based on period format."""
        if not period:
            return "unknown"
        period = period.strip()
        if len(period) == 4:
            return "annual"
        if "Q" in period.upper():
            return "quarterly"
        if len(period) == 7:  # YYYY-MM
            return "monthly"
        if len(period) == 10:  # YYYY-MM-DD
            return "monthly"
        return "annual"

    @staticmethod
    def _normalize_period_date(period: str) -> str:
        """Convert an EIA period value to an ISO date string (YYYY-MM-DD)."""
        period = period.strip()
        if len(period) == 4:
            return f"{period}-01-01"
        if "Q" in period.upper():
            parts = period.upper().replace("Q", "").split("-")
            if len(parts) == 2:
                year, quarter = parts[0], int(parts[1])
                month = (quarter - 1) * 3 + 1
                return f"{year}-{month:02d}-01"
            return f"{period[:4]}-01-01"
        if len(period) == 7:
            return f"{period}-01"
        if len(period) >= 10:
            return period[:10]
        return period
