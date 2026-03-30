"""
Trade flows domain processor.

Normalises raw EIA coal export rows into storage-ready records for the
trade_flows table. Extracts exporter/importer, coal type, volume, and
value information.
"""

from __future__ import annotations

import logging
from typing import Any

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)

# EIA coal type ID -> human-readable label
COAL_TYPE_MAP = {
    "BIT": "bituminous",
    "SUB": "subbituminous",
    "LIG": "lignite",
    "ANT": "anthracite",
    "COK": "coke",
    "TOT": "total",
}

# Approximate short tons to metric tonnes conversion
SHORT_TONS_TO_MT = 0.907185


class TradeFlowProcessor(BaseProcessor):
    """Transform raw EIA coal export data into normalised trade flow records."""

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        trade_rows = raw_data.get("trade_flows") or []

        for row in trade_rows:
            try:
                rec = self._process_export_row(row)
                if rec is not None:
                    records.append(rec)
            except Exception as exc:
                logger.debug("Skipping trade flow row: %s -- %s", row, exc)

        logger.info("TradeFlowProcessor produced %d records", len(records))
        return records

    # ------------------------------------------------------------------ #
    #  Row-level processing
    # ------------------------------------------------------------------ #
    def _process_export_row(self, row: dict) -> dict[str, Any] | None:
        """Convert a single EIA export row to a storage record."""
        # Quantity (typically in thousand short tons)
        quantity_raw = row.get("quantity")
        if quantity_raw is None:
            return None

        try:
            quantity = float(quantity_raw)
        except (ValueError, TypeError):
            return None

        # Convert to metric tonnes (million metric tonnes for readability)
        # EIA data is in thousand short tons
        volume_mt = round(quantity * 1000 * SHORT_TONS_TO_MT / 1_000_000, 4)

        # Extract destination country / region
        importer = self._extract_importer(row)

        # Exporter is always US for this endpoint
        exporter = "US"

        # Coal type
        coal_type_id = (
            row.get("coalTypeId")
            or row.get("coaltypeid")
            or row.get("coal-type-id")
            or "TOT"
        )
        coal_type = COAL_TYPE_MAP.get(
            str(coal_type_id).upper(),
            str(coal_type_id).lower(),
        )

        # Period
        period = row.get("period", "")
        period_date = self._normalize_period_date(period)

        # Value (if available)
        value_raw = row.get("value") or row.get("revenue")
        value_usd = None
        if value_raw is not None:
            try:
                value_usd = float(value_raw)
            except (ValueError, TypeError):
                pass

        return {
            "_table": "trade_flows",
            "exporter": exporter,
            "importer": importer,
            "coal_type": coal_type,
            "volume_mt": volume_mt,
            "value_usd": value_usd,
            "period_date": period_date,
            "source": "eia",
        }

    # ------------------------------------------------------------------ #
    #  Utility methods
    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_importer(row: dict) -> str:
        """Extract the destination country from an EIA export row."""
        for key in (
            "countryRegionName", "countryregionname",
            "customsDistrictDescription", "customsdistrictdescription",
            "destinationId", "destinationid",
            "countryRegionId", "countryregionid",
        ):
            val = row.get(key)
            if val and str(val).strip():
                return str(val).strip()
        return "Unknown"

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
