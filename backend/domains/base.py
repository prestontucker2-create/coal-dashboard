from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime, timezone
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    def __init__(self, config: dict, http_client: httpx.AsyncClient):
        self.config = config
        self.client = http_client

    @abstractmethod
    async def fetch(self, **kwargs) -> dict[str, Any]:
        ...

    async def fetch_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> httpx.Response:
        for attempt in range(max_retries):
            try:
                resp = await self.client.get(url, **kwargs)
                resp.raise_for_status()
                return resp
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt
                logger.warning(f"Retry {attempt + 1}/{max_retries} for {url}: {e}. Waiting {wait}s")
                await asyncio.sleep(wait)


class BaseProcessor(ABC):
    @abstractmethod
    def process(self, raw_data: dict[str, Any]) -> list[dict[str, Any]]:
        ...


class BaseStorage(ABC):
    def __init__(self, db):
        self.db = db

    @abstractmethod
    async def store(self, records: list[dict[str, Any]]) -> int:
        ...

    @abstractmethod
    async def query(self, filters: dict, timeframe: str = "1Y") -> list[dict[str, Any]]:
        ...

    def timeframe_to_days(self, timeframe: str) -> int:
        mapping = {
            "1W": 7, "1M": 30, "3M": 90, "6M": 180,
            "1Y": 365, "3Y": 1095, "ALL": 36500,
        }
        return mapping.get(timeframe, 365)


class DomainOrchestrator:
    def __init__(
        self,
        fetcher: BaseFetcher,
        processor: BaseProcessor,
        storage: BaseStorage,
        source_name: str,
        domain: str,
        db,
    ):
        self.fetcher = fetcher
        self.processor = processor
        self.storage = storage
        self.source_name = source_name
        self.domain = domain
        self.db = db

    async def run(self, **fetch_kwargs) -> int:
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._update_freshness(last_attempt=now)
            raw_data = await self.fetcher.fetch(**fetch_kwargs)
            records = self.processor.process(raw_data)
            count = await self.storage.store(records)
            await self._update_freshness(last_success=now, record_count=count)
            logger.info(f"[{self.source_name}] Stored {count} records")
            return count
        except Exception as e:
            logger.error(f"[{self.source_name}] Pipeline error: {e}")
            await self._update_freshness(last_error=str(e))
            return 0

    async def _update_freshness(self, **kwargs):
        from sqlalchemy import text
        async with self.db.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    text("SELECT id FROM data_freshness WHERE source_name = :s"),
                    {"s": self.source_name},
                )
                exists = result.fetchone()

                if exists:
                    sets = []
                    params = {"s": self.source_name}
                    for k, v in kwargs.items():
                        sets.append(f"{k} = :{k}")
                        params[k] = v
                    if sets:
                        await session.execute(
                            text(f"UPDATE data_freshness SET {', '.join(sets)} WHERE source_name = :s"),
                            params,
                        )
                else:
                    params = {
                        "source_name": self.source_name,
                        "domain": self.domain,
                        **kwargs,
                    }
                    cols = ", ".join(params.keys())
                    vals = ", ".join(f":{k}" for k in params.keys())
                    await session.execute(
                        text(f"INSERT INTO data_freshness ({cols}) VALUES ({vals})"),
                        params,
                    )
