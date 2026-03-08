"""
Async SQLite database
"""

import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


logger = logging.getLogger(__name__)


DB_DIR = Path("/data")
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "bot_database.db"


logger.info("Database path: %s", DB_PATH)

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable foreign key constraints for SQLite connections.
    This function is called whenever a new database connection is created.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Creates and yields an async database session."""
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initializes the database by creating all tables and setting up default values."""
    try:
        logger.info("Initializing database at: %s", DB_PATH)

        async with engine.begin() as conn:
            from models.admin_state import AdminState  # noqa: F401
            from models.questions import Question  # noqa: F401
            from models.settings import BotSettings  # noqa: F401
            from models.user_states import UserState  # noqa: F401

            await conn.run_sync(Base.metadata.create_all)

        await _initialize_default_settings()

        if DB_PATH.exists():
            file_size = DB_PATH.stat().st_size
            logger.info("Database initialized at %s (%d bytes)", DB_PATH, file_size)
        else:
            logger.warning("Database file not found at %s", DB_PATH)

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """Properly closes the database engine and releases all connections."""
    try:
        await engine.dispose()
        logger.info("Database closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


async def check_db_connection() -> bool:
    """Tests if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        async with async_session() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def _initialize_default_settings() -> None:
    """
    Sets up default application settings in the database.
    This function checks for the existence of essential settings
    and creates them with default values if they are missing.
    """
    try:
        from models.settings import BotSettings, SettingsManager

        async with async_session() as session:
            for key in ["author_name", "author_info"]:
                if not await session.get(BotSettings, key):
                    session.add(
                        BotSettings(
                            key=key, value=SettingsManager.DEFAULT_SETTINGS[key]
                        )
                    )
            await session.commit()
            logger.info("Default settings initialized")

    except Exception as e:
        logger.error(f"Failed to initialize settings: {e}")


async def check_persistence() -> dict:
    """
    Check if database persists between restarts.
    Returns info about database file and tables.
    """
    info = {
        "db_path": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "size": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "tables": [],
    }

    if DB_PATH.exists():
        try:
            async with async_session() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
                tables = [row[0] for row in result.fetchall()]
                info["tables"] = tables
        except Exception as e:
            info["error"] = str(e)

    return info
