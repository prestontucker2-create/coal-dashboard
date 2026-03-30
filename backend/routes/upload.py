import csv
import io
from fastapi import APIRouter, UploadFile, File, Query
from sqlalchemy import text

router = APIRouter()

UPLOAD_SCHEMAS = {
    "met_coal_prices": {
        "table": "coal_prices",
        "columns": {"date": "timestamp", "benchmark": "benchmark", "price_usd": "price_usd"},
        "defaults": {"source": "csv_upload", "currency": "USD"},
    },
    "freight_rates": {
        "table": "macro_indicators",
        "columns": {"date": "timestamp", "route": "indicator", "rate_usd": "value"},
        "defaults": {"source": "csv_upload"},
        "prefix": "freight_",
    },
    "port_stockpiles": {
        "table": "coal_inventories",
        "columns": {"date": "period_date", "port_name": "location", "stockpile_mt": "inventory_tons"},
        "defaults": {"source": "csv_upload"},
    },
    "mine_disruptions": {
        "table": "international_supply",
        "columns": {"date": "period_date", "country": "country", "event": "metric", "impact_mt": "value"},
        "defaults": {"source": "csv_upload", "unit": "mt"},
    },
}


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    type: str = Query(..., description="Upload type: met_coal_prices, freight_rates, port_stockpiles, mine_disruptions"),
):
    if type not in UPLOAD_SCHEMAS:
        return {"error": f"Unknown type '{type}'", "available": list(UPLOAD_SCHEMAS.keys())}

    schema = UPLOAD_SCHEMAS[type]
    content = await file.read()
    text_content = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text_content))

    rows_inserted = 0
    errors = []

    from main import _db
    async with _db.session_factory() as session:
        async with session.begin():
            for i, row in enumerate(reader):
                try:
                    record = {}
                    for csv_col, db_col in schema["columns"].items():
                        if csv_col not in row:
                            raise ValueError(f"Missing column: {csv_col}")
                        val = row[csv_col].strip()
                        if db_col in ("price_usd", "value", "inventory_tons", "rate_usd"):
                            val = float(val)
                        if "prefix" in schema and db_col == "indicator":
                            val = schema["prefix"] + val
                        record[db_col] = val

                    for k, v in schema.get("defaults", {}).items():
                        record[k] = v

                    cols = ", ".join(record.keys())
                    vals = ", ".join(f":{k}" for k in record.keys())
                    await session.execute(
                        text(f"INSERT OR REPLACE INTO {schema['table']} ({cols}) VALUES ({vals})"),
                        record,
                    )
                    rows_inserted += 1
                except Exception as e:
                    errors.append(f"Row {i + 1}: {e}")

            # Log upload
            await session.execute(
                text("INSERT INTO csv_uploads (upload_type, filename, rows_inserted) VALUES (:t, :f, :r)"),
                {"t": type, "f": file.filename, "r": rows_inserted},
            )

    return {
        "status": "ok",
        "rows_inserted": rows_inserted,
        "errors": errors[:10] if errors else [],
    }
