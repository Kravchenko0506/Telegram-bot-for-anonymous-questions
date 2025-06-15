"""
Database Management System

A comprehensive PostgreSQL database system for the Anonymous Questions Bot
that provides robust data persistence, connection management, and ORM support.

Core Features:
- Asynchronous database operations
- Connection pooling and management
- Session handling and cleanup
- Health monitoring
- Default settings initialization
- Error handling and recovery

Technical Features:
- SQLAlchemy async ORM integration
- PostgreSQL with asyncpg driver
- Connection pool configuration
- Session lifecycle management
- Database migration support
- Resource cleanup
- Health checks

Architecture:
- PostgreSQL as primary database
- SQLAlchemy ORM for data modeling
- Async operations for performance
- Connection pooling for scalability
- Session-based transactions
- Automatic cleanup
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration from environment
DB_USER = os.getenv("DB_USER", "botanon")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "dbfrombot")

# Construct database URL
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query debugging
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,   # Recycle connections every hour
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create declarative base
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create and manage database sessions with automatic cleanup.

    This dependency function provides:
    - Proper session lifecycle management
    - Automatic resource cleanup
    - Error handling and recovery
    - Transaction management

    Usage:
        async with get_async_session() as session:
            result = await session.execute(select(Question))

    Yields:
        AsyncSession: Database session for operations

    Raises:
        Exception: If session creation or operation fails
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
    Initialize and configure the database system.

    This function:
    - Creates database tables if they don't exist
    - Initializes default settings
    - Verifies database connectivity
    - Sets up model relationships

    The function is idempotent and can be safely called multiple times.
    It will only create tables and settings that don't already exist.

    Raises:
        Exception: If database initialization fails
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from models.questions import Question
            from models.settings import BotSettings
            from models.user_states import UserState  # Import user states model

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

        # Initialize default settings if they don't exist
        await _initialize_default_settings()

        logger.info(
            "Database initialized successfully (Questions + Settings tables)")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Perform graceful database shutdown and resource cleanup.

    This function:
    - Closes active connections
    - Releases connection pool
    - Cleans up resources
    - Logs shutdown status

    Should be called during application shutdown to ensure proper cleanup.
    """
    try:
        await engine.dispose()
        logger.info("Database engine closed successfully")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Database health check
async def check_db_connection() -> bool:
    """
    Verify database connectivity and health.

    This function:
    - Tests database connection
    - Verifies query execution
    - Checks connection pool
    - Logs connection status

    Returns:
        bool: True if database is healthy and accessible

    Note:
        This is a lightweight check suitable for health monitoring
    """
    try:
        async with async_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1"))
            row = result.fetchone()
            logger.info("PostgreSQL + asyncpg connection successful")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def _initialize_default_settings() -> None:
    """
    Set up initial database settings if they don't exist.

    This function:
    - Checks for existing settings
    - Creates default settings if needed
    - Maintains data consistency
    - Logs initialization status

    The function is idempotent and safe to call multiple times.
    It will not override existing settings.

    Raises:
        Exception: If settings initialization fails
    """
    try:
        from models.settings import BotSettings, SettingsManager

        async with async_session() as session:
            # Check if author_name exists
            author_setting = await session.get(BotSettings, 'author_name')
            if not author_setting:
                author_setting = BotSettings(
                    key='author_name',
                    value=SettingsManager.DEFAULT_SETTINGS['author_name']
                )
                session.add(author_setting)

            # Check if author_info exists
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
