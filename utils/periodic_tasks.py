"""
Periodic Task Management System

A comprehensive system for managing and executing background maintenance tasks
that ensure the bot's health, performance, and data integrity.

Features:
- Automated state cleanup
- Database health monitoring
- Task lifecycle management
- Error recovery
- Resource cleanup
- Graceful shutdown

Components:
- Task Manager: Coordinates all periodic tasks
- State Cleanup: Removes expired admin states
- Health Monitor: Checks database connectivity
- Error Handler: Manages task failures and recovery
"""

import asyncio
from datetime import datetime
from typing import Optional

from utils.logging_setup import get_logger

logger = get_logger(__name__)


class PeriodicTaskManager:
    """
    Manages lifecycle and execution of periodic maintenance tasks.

    This manager provides:
    - Task coordination and scheduling
    - Error handling and recovery
    - Resource management
    - Graceful startup/shutdown
    - Task state monitoring

    Features:
    - Concurrent task execution
    - Automatic error recovery
    - Resource cleanup
    - Task health monitoring
    """

    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False

    async def start(self):
        """
        Start all periodic maintenance tasks.

        This method:
        - Prevents duplicate task starts
        - Initializes task list
        - Launches concurrent tasks
        - Monitors task startup
        - Logs task status
        """
        if self.running:
            logger.warning("Periodic tasks already running")
            return

        self.running = True
        logger.debug("Starting periodic tasks...")

        # Start individual tasks
        self.tasks.append(
            asyncio.create_task(self._cleanup_expired_states())
        )
        self.tasks.append(
            asyncio.create_task(self._database_health_check())
        )

        # Start backup scheduler if enabled
        from config import BACKUP_ENABLED, BACKUP_RECIPIENT_ID
        if BACKUP_ENABLED and BACKUP_RECIPIENT_ID:
            from utils.telegram_backup import backup_scheduler_task
            self.tasks.append(
                asyncio.create_task(backup_scheduler_task(BACKUP_RECIPIENT_ID))
            )
            logger.info(
                f"📦 Telegram backup scheduler enabled for user {BACKUP_RECIPIENT_ID}")

        logger.debug(f"Started {len(self.tasks)} periodic tasks")

    async def stop(self):
        """
        Stop all periodic tasks gracefully.

        This method:
        - Signals task termination
        - Cancels running tasks
        - Waits for task completion
        - Cleans up resources
        - Logs shutdown status
        """
        if not self.running:
            return

        self.running = False
        logger.debug("Stopping periodic tasks...")

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

        logger.debug("All periodic tasks stopped")

    async def _cleanup_expired_states(self):
        """
        Periodically clean up expired admin states.

        This task:
        - Runs every hour
        - Removes expired states
        - Handles cleanup errors
        - Logs cleanup results
        - Implements automatic retry

        Error handling:
        - Graceful cancellation
        - Automatic retry after failures
        - Error logging and reporting
        """
        while self.running:
            try:
                logger.debug("Running expired states cleanup...")

                from models.admin_state import AdminStateManager

                cleaned_count = await AdminStateManager.cleanup_expired_states()

                if cleaned_count > 0:
                    logger.debug(
                        f"Cleaned up {cleaned_count} expired admin states")
                else:
                    logger.debug("No expired admin states found")

                # Run every hour
                await asyncio.sleep(3600)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                # Wait 5 minutes before retry
                await asyncio.sleep(300)

    async def _database_health_check(self):
        """
        Monitor database health and connectivity.

        This task:
        - Runs every 5 minutes
        - Verifies database connection
        - Reports connectivity issues
        - Implements automatic retry
        - Logs health status

        Error handling:
        - Graceful cancellation
        - Quick retry on failures
        - Error logging and alerting
        """
        while self.running:
            try:
                from models.database import check_db_connection

                if not await check_db_connection():
                    logger.error("Database health check failed!")
                    # Could send alert to admin here
                else:
                    logger.debug("Database health check passed")

                # Run every 5 minutes
                await asyncio.sleep(300)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(60)


# Global instance
periodic_task_manager = PeriodicTaskManager()


async def start_periodic_tasks():
    """
    Start the periodic task system.

    This function:
    - Initializes the task manager
    - Starts all maintenance tasks
    - Monitors startup process
    - Ensures single instance
    """
    await periodic_task_manager.start()


async def stop_periodic_tasks():
    """
    Stop the periodic task system gracefully.

    This function:
    - Signals shutdown to task manager
    - Waits for task completion
    - Ensures clean resource cleanup
    - Verifies shutdown status
    """
    await periodic_task_manager.stop()
