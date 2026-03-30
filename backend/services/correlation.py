import logging
from datetime import datetime, timedelta
from sqlalchemy import text
import numpy as np

logger = logging.getLogger(__name__)

# Series definitions: (label, table, value_col, date_col, filter_clause)
SERIES_DEFS = [
    ("Newcastle Coal", "coal_prices", "price_usd", "timestamp", "benchmark = 'newcastle'"),
    ("Henry Hub Gas", "gas_prices", "price", "timestamp", "benchmark = 'henry_hub'"),
    ("AUD/USD", "macro_indicators", "value", "timestamp", "indicator = 'audusd'"),
    ("DXY", "macro_indicators", "value", "timestamp", "indicator = 'dxy'"),
    ("US 10Y Yield", "macro_indicators", "value", "timestamp", "indicator = 'us10y'"),
    ("BTU Price", "stock_prices", "close", "date", "ticker = 'BTU'"),
    ("WHC.AX Price", "stock_prices", "close", "date", "ticker = 'WHC.AX'"),
]


class CorrelationService:
    def __init__(self, db):
        self.db = db

    async def calculate_matrix(self, timeframe: str = "1Y") -> dict:
        days = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 1095}.get(timeframe, 365)
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        series_data = {}
        labels = []

        async with self.db.session_factory() as session:
            for label, table, val_col, date_col, where in SERIES_DEFS:
                query = f"SELECT date({date_col}) as d, {val_col} FROM {table} WHERE {where} AND {date_col} >= :cutoff ORDER BY d"
                result = await session.execute(text(query), {"cutoff": cutoff})
                rows = result.fetchall()

                if len(rows) >= 10:
                    series_data[label] = {str(r[0]): float(r[1]) for r in rows if r[1] is not None}
                    labels.append(label)

        if len(labels) < 2:
            return {"labels": labels, "matrix": [], "message": "Insufficient data for correlation"}

        # Align series on common dates
        all_dates = set()
        for data in series_data.values():
            all_dates.update(data.keys())
        common_dates = sorted(all_dates)

        # Build matrix of aligned values
        aligned = {}
        for label in labels:
            vals = []
            for d in common_dates:
                if d in series_data[label]:
                    vals.append(series_data[label][d])
                else:
                    vals.append(None)
            aligned[label] = vals

        # Forward-fill gaps
        for label in labels:
            arr = aligned[label]
            for i in range(1, len(arr)):
                if arr[i] is None:
                    arr[i] = arr[i - 1]

        # Calculate correlations
        n = len(labels)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                    continue

                x = [aligned[labels[i]][k] for k in range(len(common_dates)) if aligned[labels[i]][k] is not None and aligned[labels[j]][k] is not None]
                y = [aligned[labels[j]][k] for k in range(len(common_dates)) if aligned[labels[i]][k] is not None and aligned[labels[j]][k] is not None]

                if len(x) < 10:
                    matrix[i][j] = 0.0
                    continue

                x_arr = np.array(x, dtype=float)
                y_arr = np.array(y, dtype=float)

                if np.std(x_arr) == 0 or np.std(y_arr) == 0:
                    matrix[i][j] = 0.0
                else:
                    corr = np.corrcoef(x_arr, y_arr)[0, 1]
                    matrix[i][j] = round(float(corr), 4)

        return {"labels": labels, "matrix": matrix}
