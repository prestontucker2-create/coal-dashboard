import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(os.path.abspath(db_path))
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Database path: {os.path.abspath(db_path)}")

        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init(self):
        async with self.engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=5000"))
            await conn.execute(text("PRAGMA synchronous=NORMAL"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
        await self.run_migrations()

    async def run_migrations(self):
        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            logger.warning("No migrations directory found")
            return

        migration_files = sorted(migrations_dir.glob("*.sql"))
        async with self.engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))

            for mf in migration_files:
                result = await conn.execute(
                    text("SELECT 1 FROM _migrations WHERE filename = :f"),
                    {"f": mf.name},
                )
                if result.fetchone():
                    continue

                logger.info(f"Applying migration: {mf.name}")
                sql = mf.read_text()
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        await conn.execute(text(statement))

                await conn.execute(
                    text("INSERT INTO _migrations (filename) VALUES (:f)"),
                    {"f": mf.name},
                )

        logger.info("Migrations complete")

    def get_session(self) -> AsyncSession:
        return self.session_factory()

    async def close(self):
        await self.engine.dispose()
