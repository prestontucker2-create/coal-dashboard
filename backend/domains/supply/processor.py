"""
Supply domain processor -- normalises raw EIA production and inventory rows
into records ready for storage.
"""

from typing import Any
from datetime import datetime
import logging

from domains.base import BaseProcessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------
# EIA mine-production values come in *thousand short tons*.
THOUSAND_SHORT_TONS_TO_TONS = 1_000.0

# Average daily US coal consumption (approximate, for days-of-supply calc).
# ~500 million short tons per year  =>  ~1.37 million tons/day.
_DEFAULT_DAILY_CONSUMPTION_TONS = 1_370_000.0


class SupplyProcessor(BaseProcessor):
    """
    Transform raw EIA JSON rows into flat dicts for the ``us_coal_production``
    and ``coal_inventories`` tables.
    """

    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        production_rows = raw_data.get("production") or []
        inventory_rows = raw_data.get("inventories") or []

        records.extend(self._process_production(production_rows))
        records.extend(self._process_inventories(inventory_rows))

        logger.info(
            "SupplyProcessor produced %d total records "
            "(%d production, %d inventory)",
            len(records),
            len([r for r in records if r["_table"] == "production"]),
            len([r for r in records if r["_table"] == "inventory"]),
        )
        return records

    # ----- production ------------------------------------------------------

    def _process_production(
        self, rows: list[dict],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        # Group by region+period so we can compute YoY later
        by_region: dict[str, list[dict]] = {}

        for row in rows:
            try:
                region = self._extract_region(row)
                period = row.get("period", "")
                period_type = self._infer_period_type(period)
                production_raw = row.get("production")
                if production_raw is None:
                    continue

                production_tons = (
                    float(production_raw) * THOUSAND_SHORT_TONS_TO_TONS
                )
                period_date = self._normalize_period_date(period)

                rec = {
                    "_table": "production",
                    "region": region,
                    "production_tons": round(production_tons, 2),
                    "period_type": period_type,
                    "period_date": period_date,
                    "source": "eia",
                }
                records.append(rec)
                by_region.setdefault(region, []).append(rec)

            except Exception as exc:
                logger.debug("Skipping production row: %s -- %s", row, exc)

        # Attach YoY change where possible
        self._attach_yoy(by_region)

        return records

    # ----- inventories -----------------------------------------------------

    def _process_inventories(
        self, rows: list[dict],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in rows:
            try:
                location = row.get("statedescription") or row.get(
                    "sectorDescription"
                ) or row.get("stateid", "US")
                period = row.get("period", "")
                period_date = self._normalize_period_date(period)

                coal_stocks = row.get("coal-stocks") or row.get(
                    "coalstocks"
                )
                if coal_stocks is None:
                    continue

                inventory_tons = (
                    float(coal_stocks) * THOUSAND_SHORT_TONS_TO_TONS
                )
                days_supply = self._estimate_days_supply(inventory_tons)

                records.append(
                    {
                        "_table": "inventory",
                        "location": str(location),
                        "inventory_tons": round(inventory_tons, 2),
                        "days_supply": round(days_supply, 1) if days_supply else None,
                        "period_date": period_date,
                        "source": "eia",
                    }
                )
            except Exception as exc:
                logger.debug("Skipping inventory row: %s -- %s", row, exc)

        return records

    # ----- utility methods -------------------------------------------------

    @staticmethod
    def _extract_region(row: dict) -> str:
        """Best-effort region from an EIA mine-production row."""
        for key in ("mine-state", "mineState", "statedescription", "stateid"):
            val = row.get(key)
            if val:
                return str(val)
        return "total"

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
            # e.g. "2024-Q1" -> "2024-01-01"
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

    @staticmethod
    def _estimate_days_supply(
        inventory_tons: float,
        daily_consumption: float = _DEFAULT_DAILY_CONSUMPTION_TONS,
    ) -> float | None:
        """Rough days-of-supply = inventory / daily average consumption."""
        if daily_consumption <= 0 or inventory_tons <= 0:
            return None
        return inventory_tons / daily_consumption

    @staticmethod
    def _attach_yoy(
        by_region: dict[str, list[dict]],
    ) -> None:
        """
        For each region, sort records chronologically and attach a
        ``yoy_change_pct`` field where the previous year's value is available.
        """
        for region, recs in by_region.items():
            recs.sort(key=lambda r: r["period_date"])
            by_year: dict[str, dict] = {}
            for rec in recs:
                year = rec["period_date"][:4]
                by_year[year] = rec

            for rec in recs:
                year = rec["period_date"][:4]
                try:
                    prev_year = str(int(year) - 1)
                except ValueError:
                    continue
                prev = by_year.get(prev_year)
                if prev and prev["production_tons"] > 0:
                    change = (
                        (rec["production_tons"] - prev["production_tons"])
                        / prev["production_tons"]
                        * 100
                    )
                    rec["yoy_change_pct"] = round(change, 2)
