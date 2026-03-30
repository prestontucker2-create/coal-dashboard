"""
Weather domain fetcher.

Pulls ENSO status and heating/cooling degree day (HDD/CDD) data from NOAA,
which affect coal demand through electricity generation for heating and cooling.

Sources:
- NOAA ENSO: ONI (Oceanic Nino Index) data from fixed-width text file
- NOAA HDD/CDD: Weekly degree day data from CPC text file
"""

from __future__ import annotations

import logging
import re
from typing import Any

from domains.base import BaseFetcher

logger = logging.getLogger(__name__)

# NOAA endpoints
ENSO_ONI_URL = (
    "https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/"
    "ensostuff/detrend.nino34.ascii.txt"
)
ENSO_ADVISORY_URL = (
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
    "enso_advisory/ensodisc.html"
)
DEGREE_DAYS_URL = (
    "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
    "cdus/degree_days/wsccdd.txt"
)


class WeatherFetcher(BaseFetcher):
    """Fetch ENSO status and degree day data from NOAA."""

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #
    async def fetch(self, **kwargs) -> dict[str, Any]:
        enso_data = await self._fetch_enso()
        degree_days = await self._fetch_degree_days()

        logger.info(
            "WeatherFetcher complete: %d ENSO records, %d degree day records",
            len(enso_data),
            len(degree_days),
        )
        return {"enso": enso_data, "degree_days": degree_days}

    # ------------------------------------------------------------------ #
    #  ENSO / ONI data
    # ------------------------------------------------------------------ #
    async def _fetch_enso(self) -> list[dict]:
        """Fetch the detrended Nino 3.4 SST anomaly data (ONI proxy).

        The file is a fixed-width text file with columns:
        YR MON APTS SPTS  (Year, Month, Anomaly-Pacific-Tropical-South, ...)
        We extract ONI-like values from the anomaly columns.
        """
        records: list[dict] = []

        try:
            resp = await self.fetch_with_retry(ENSO_ONI_URL, timeout=20.0)
            text_content = resp.text
            records = self._parse_oni_data(text_content)
            logger.info("ENSO ONI: parsed %d records", len(records))
        except Exception as exc:
            logger.warning("ENSO ONI fetch failed: %s", exc)

        # Fallback: try to scrape advisory page for current status
        if not records:
            try:
                records = await self._fetch_enso_advisory()
            except Exception as exc:
                logger.warning("ENSO advisory fetch also failed: %s", exc)

        return records

    def _parse_oni_data(self, text_content: str) -> list[dict]:
        """Parse the fixed-width ONI / Nino 3.4 anomaly text file.

        Expected format (space-delimited):
            YR   MON   TOTAL   ClimAdj   APTS    SPTS
        We use the last numeric column as the anomaly value.
        """
        records: list[dict] = []
        lines = text_content.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            # First two columns should be year and month
            try:
                year = int(parts[0])
                month = int(parts[1])
            except (ValueError, IndexError):
                continue

            if year < 1950 or month < 1 or month > 12:
                continue

            # Use the last numeric value as the anomaly
            anomaly = None
            for val_str in reversed(parts[2:]):
                try:
                    anomaly = float(val_str)
                    break
                except ValueError:
                    continue

            if anomaly is None:
                continue

            # Classify ENSO phase based on ONI thresholds
            if anomaly >= 0.5:
                phase = "El Nino"
            elif anomaly <= -0.5:
                phase = "La Nina"
            else:
                phase = "Neutral"

            records.append({
                "oni_value": round(anomaly, 2),
                "phase": phase,
                "period_date": f"{year}-{month:02d}-01",
            })

        return records

    async def _fetch_enso_advisory(self) -> list[dict]:
        """Scrape the ENSO advisory page for current status as a fallback."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not available -- cannot parse ENSO advisory HTML")
            return []

        resp = await self.fetch_with_retry(ENSO_ADVISORY_URL, timeout=20.0)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for synopsis text containing phase information
        text_content = soup.get_text(separator=" ", strip=True).lower()

        phase = "Neutral"
        oni_value = 0.0

        if "el nino" in text_content or "el niño" in text_content:
            phase = "El Nino"
            oni_value = 0.8  # approximate placeholder
        elif "la nina" in text_content or "la niña" in text_content:
            phase = "La Nina"
            oni_value = -0.8

        # Try to extract an actual ONI value from the text
        oni_match = re.search(r'oni\s*(?:value|index)?[:\s]*([+-]?\d+\.?\d*)', text_content)
        if oni_match:
            try:
                oni_value = float(oni_match.group(1))
            except ValueError:
                pass

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        return [{
            "oni_value": oni_value,
            "phase": phase,
            "period_date": f"{now.year}-{now.month:02d}-01",
        }]

    # ------------------------------------------------------------------ #
    #  Degree Days (HDD / CDD)
    # ------------------------------------------------------------------ #
    async def _fetch_degree_days(self) -> list[dict]:
        """Fetch weekly heating and cooling degree day data from NOAA CPC.

        The file is a fixed-width text file with regional HDD/CDD values.
        """
        records: list[dict] = []

        try:
            resp = await self.fetch_with_retry(DEGREE_DAYS_URL, timeout=20.0)
            text_content = resp.text
            records = self._parse_degree_days(text_content)
            logger.info("Degree days: parsed %d records", len(records))
        except Exception as exc:
            logger.warning("Degree days fetch failed: %s", exc)

        return records

    def _parse_degree_days(self, text_content: str) -> list[dict]:
        """Parse NOAA CPC degree day text file.

        The file contains sections for different regions with HDD and CDD
        values. We extract weekly totals, deviations from normal, and
        region identifiers.
        """
        records: list[dict] = []
        lines = text_content.strip().split("\n")

        current_region = "US"
        current_date = None
        in_data_section = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Look for date patterns in header lines (e.g., "Week ending 01/15/2025")
            date_match = re.search(
                r'(?:week\s+ending|ending)\s+(\d{1,2})/(\d{1,2})/(\d{4})',
                stripped,
                re.IGNORECASE,
            )
            if date_match:
                month, day, year = date_match.groups()
                current_date = f"{year}-{int(month):02d}-{int(day):02d}"
                in_data_section = True
                continue

            # Look for region headers
            region_match = re.search(
                r'^(US|United States|Northeast|Midwest|South|West|'
                r'East North Central|West North Central|'
                r'South Atlantic|East South Central|West South Central|'
                r'Mountain|Pacific)',
                stripped,
                re.IGNORECASE,
            )
            if region_match:
                current_region = region_match.group(1).strip()
                continue

            # Parse numeric data rows
            if in_data_section and current_date:
                parts = stripped.split()
                # Try to extract HDD and CDD values from numeric rows
                numeric_parts = []
                for p in parts:
                    try:
                        numeric_parts.append(float(p))
                    except ValueError:
                        # This might be a region label within the data row
                        if len(p) > 1 and p.replace(" ", "").isalpha():
                            current_region = p
                        continue

                if len(numeric_parts) >= 2:
                    # Typically: actual, normal, deviation
                    hdd = numeric_parts[0]
                    deviation = numeric_parts[2] if len(numeric_parts) >= 3 else None

                    records.append({
                        "region": current_region,
                        "hdd": hdd,
                        "cdd": numeric_parts[1] if len(numeric_parts) >= 4 else None,
                        "deviation_from_normal": deviation,
                        "period_date": current_date,
                    })

        # If parsing yielded nothing useful, create a minimal fallback
        # with the raw text available for inspection
        if not records:
            logger.info(
                "Degree days parsing returned 0 structured records; "
                "raw text length: %d chars", len(text_content)
            )

        return records
