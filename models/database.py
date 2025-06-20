"""
Database Management System with SQLite

This module provides an asynchronous SQLite database interface using SQLAlchemy.
It handles database connection, session management, and basic operations.

The module sets up:
- Async SQLite engine with foreign key support
- Session factory for async database operations
- Base declarative class for ORM models
- Database initialization and connection management functions

Note on datetime handling:
- SQLite stores datetimes as naive (without timezone info)
- All timestamps are stored in UTC but without timezone information
- Application code handles timezone conversion when needed
"""

import os
import logging
from typing import AsyncGenerator
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# ИСПРАВЛЕНО: Используем абсолютный путь для Amvera persistent storage
DB_DIR = Path("/data")  # ✅ Правильный путь для Amvera
DB_DIR.mkdir(exist_ok=True)

# Database file path в персистентном хранилище
DB_PATH = DB_DIR / "bot_database.db"

# Логируем где будет база данных
print(f"🗄️ Database will be stored at: {DB_PATH}")
logger.info(f"Database path: {DB_PATH}")

# SQLite connection string
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query debugging
    connect_args={"check_same_thread": False},  # Required for SQLite
)

# Enable foreign key support for SQLite
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Enable foreign key constraints for SQLite connections.
    This function is called whenever a new database connection is created.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base for ORM models
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates and yields an async database session.

    Yields:
        AsyncSession: An active database session

    Notes:
        - Uses context manager to ensure proper session cleanup
        - Implements error handling and rollback on exceptions
    """
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
    """
    Initializes the database by creating all tables and setting up default values.

    This function:
    1. Creates database tables based on imported models
    2. Sets up default settings values

    Raises:
        Exception: If database initialization fails
    """
    try:
        # Проверяем что база будет создана в правильном месте
        print(f"🔧 Initializing database at: {DB_PATH}")
        
        async with engine.begin() as conn:
            from models.questions import Question
            from models.settings import BotSettings
            from models.user_states import UserState
            from models.admin_state import AdminState

            await conn.run_sync(Base.metadata.create_all)

        await _initialize_default_settings()
        
        # Проверяем что файл действительно создался
        if DB_PATH.exists():
            file_size = DB_PATH.stat().st_size
            print(f"✅ Database file created: {DB_PATH} (size: {file_size} bytes)")
            logger.info(f"SQLite database initialized successfully at {DB_PATH}")
        else:
            print(f"❌ Database file not found at {DB_PATH}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        print(f"❌ Database initialization failed: {e}")
        raise


async def close_db() -> None:
    """
    Properly closes the database engine and releases all connections.

    Should be called when shutting down the application.
    """
    try:
        await engine.dispose()
        logger.info("Database engine closed successfully")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


async def check_db_connection() -> bool:
    """
    Tests if database connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        async with async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            row = result.fetchone()            
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        print(f"❌ Database connection failed: {e}")
        return False


async def _initialize_default_settings() -> None:
    """
    Sets up default application settings in the database.

    This function is called during database initialization to ensure
    required settings exist in the database with default values.

    Private function intended to be called only by init_db().
    """
    try:
        from models.settings import BotSettings, SettingsManager

        async with async_session() as session:
            author_setting = await session.get(BotSettings, 'author_name')
            if not author_setting:
                author_setting = BotSettings(
                    key='author_name',
                    value=SettingsManager.DEFAULT_SETTINGS['author_name']
                )
                session.add(author_setting)

            info_setting = await session.get(BotSettings, 'author_info')
            if not info_setting:
                info_setting = BotSettings(
                    key='author_info',
                    value=SettingsManager.DEFAULT_SETTINGS['author_info']
                )
                session.add(info_setting)

            await session.commit()
            logger.info("Default settings initialized")

    except Exception as e:
        logger.error(f"Failed to initialize default settings: {e}")


# Функция для проверки персистентности (для отладки)
async def check_persistence() -> dict:
    """
    Check if database persists between restarts.
    Returns info about database file and tables.
    """
    info = {
        "db_path": str(DB_PATH),
        "exists": DB_PATH.exists(),
        "size": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
        "tables": []
    }
    
    if DB_PATH.exists():
        try:
            async with async_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result.fetchall()]
                info["tables"] = tables
        except Exception as e:
            info["error"] = str(e)
    
    return info
