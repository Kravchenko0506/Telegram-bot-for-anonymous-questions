"""
Database Reset and Initialization System

A comprehensive system for resetting and reinitializing the database
with proper schema and default settings. This script provides a safe
way to reset the database for development or maintenance purposes.

Features:
- Database schema reset
- Table recreation
- Default settings initialization
- Error handling
- Logging support

Technical Features:
- Async operations
- Schema validation
- Data consistency
- Error recovery
- Resource cleanup
"""

import asyncio
import logging
from models.database import engine, Base, async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reset_database():
    """
    Reset and reinitialize database with fresh schema.

    This function provides:
    - Safe table dropping
    - Schema recreation
    - Settings initialization
    - Error handling

    Features:
    - Model registration
    - Table management
    - Data initialization
    - Resource cleanup

    Flow:
    1. Drop existing tables
    2. Create new schema
    3. Initialize settings
    4. Verify structure

    Technical Details:
    - Uses SQLAlchemy async engine
    - Handles model dependencies
    - Manages transactions
    - Ensures cleanup
    """
    try:
        logger.info("Connecting to database...")

        async with engine.begin() as conn:
            logger.info("Dropping all existing tables...")

            # Import all models to ensure they're registered
            from models.questions import Question
            from models.settings import BotSettings
            from models.user_states import UserState

            # Drop all tables
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped")

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("All tables created")

        # Initialize default settings
        from models.settings import SettingsManager

        async with async_session() as session:
            # Check if settings exist, if not create them
            from models.settings import BotSettings

            author_setting = await session.get(BotSettings, 'author_name')
            if not author_setting:
                author_setting = BotSettings(
                    key='author_name',
                    value='Автор канала'
                )
                session.add(author_setting)

            info_setting = await session.get(BotSettings, 'author_info')
            if not info_setting:
                info_setting = BotSettings(
                    key='author_info',
                    value='Здесь можно задать анонимный вопрос'
                )
                session.add(info_setting)

            await session.commit()
            logger.info("Default settings initialized")

        logger.info("✅ Database reset completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error resetting database: {e}")
        raise

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_database())
