"""Periodic background tasks for bot maintenance."""

import asyncio
from utils.logging_setup import get_logger
from config import BACKUP_ENABLED, BACKUP_RECIPIENT_ID

logger = get_logger(__name__)

class PeriodicTaskManager:
    """Manages periodic maintenance tasks lifecycle."""

    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False


    async def start(self):
        """Start all periodic maintenance tasks."""
        if self.running:
            logger.warning("Periodic tasks already running")
            return

        self.running = True

        self.tasks.append(asyncio.create_task(self._cleanup_expired_states()))
        self.tasks.append(asyncio.create_task(self._database_health_check()))

        if BACKUP_ENABLED and BACKUP_RECIPIENT_ID:
            from utils.telegram_backup import backup_scheduler_task
            self.tasks.append(asyncio.create_task(
                backup_scheduler_task(BACKUP_RECIPIENT_ID)))
            logger.info(
                f"📦 Telegram backup scheduler enabled for user {BACKUP_RECIPIENT_ID}")

        logger.debug(f"Started {len(self.tasks)} periodic tasks")


    async def stop(self):
        """Stop all periodic tasks gracefully."""
        if not self.running:
            return
        
        self.running = False

        for task in self.tasks:
            task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        logger.debug("All periodic tasks stopped")


    async def _cleanup_expired_states(self):
        """Clean up expired admin and user states every hour."""
        while self.running:
            try:
                from models.admin_state import AdminStateManager
                from models.user_states import UserStateManager

                admin_cleaned = await AdminStateManager.cleanup_expired_states()
                if admin_cleaned > 0:
                    logger.debug(
                        f"Cleaned up {admin_cleaned} expired admin states")

                user_cleaned = await UserStateManager.cleanup_old_states(hours=24)
                if user_cleaned > 0:
                    logger.debug(f"Cleaned up {user_cleaned} old user states")

                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)


    async def _database_health_check(self):
        """Check database connectivity."""
        while self.running:
            try:
                from models.database import check_db_connection

                if not await check_db_connection():
                    logger.error("Database health check failed!")
                else:
                    logger.debug("Database health check passed")

                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(60)


periodic_task_manager = PeriodicTaskManager()

async def start_periodic_tasks():
    """Start the periodic task system."""
    await periodic_task_manager.start()


async def stop_periodic_tasks():
    """Stop the periodic task system."""
    await periodic_task_manager.stop()
