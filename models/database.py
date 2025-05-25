"""
Database Configuration for Anonymous Questions Bot

Unified PostgreSQL setup using SQLAlchemy async engine.
This module replaces the mixed SQLite/PostgreSQL approach
with a single, consistent database configuration.

Architecture:
- PostgreSQL as primary database
- SQLAlchemy ORM for data modeling
- Async operations for better performance
- Connection pooling for scalability
"""

import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration from environment
DB_USER = os.getenv("DB_USER", "botanon")
DB_PASSWORD = os.getenv("DB_PASSWORD", "BotDB25052025") 
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

# Base class for all ORM models
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for getting database sessions.
    
    Provides proper session management with automatic cleanup.
    Use this in handlers and services for database operations.
    
    Yields:
        AsyncSession: Database session for operations
        
    Example:
        async with get_async_session() as session:
            result = await session.execute(select(Question))
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
    Initialize database tables.
    
    Creates all tables defined in models if they don't exist.
    This function is idempotent - safe to call multiple times.
    
    Raises:
        Exception: If database initialization fails
    """
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from models.questions import Question
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Close database engine and cleanup connections.
    
    Call this function when shutting down the application
    to ensure proper cleanup of database resources.
    """
    try:
        await engine.dispose()
        logger.info("Database engine closed successfully")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Database health check
async def check_db_connection() -> bool:
    """Check if database connection is healthy."""
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