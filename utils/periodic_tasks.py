"""
Periodic Tasks for Bot Maintenance

Runs background tasks to keep the bot healthy.
"""

import asyncio
from datetime import datetime
from typing import Optional

from utils.logger import get_bot_logger

logger = get_bot_logger()


class PeriodicTaskManager:
    """Manager for periodic background tasks."""
    
    def __init__(self):
        self.tasks: list[asyncio.Task] = []
        self.running = False
    
    async def start(self):
        """Start all periodic tasks."""
        if self.running:
            logger.warning("Periodic tasks already running")
            return
        
        self.running = True
        logger.info("Starting periodic tasks...")
        
        # Start individual tasks
        self.tasks.append(
            asyncio.create_task(self._cleanup_expired_states())
        )
        self.tasks.append(
            asyncio.create_task(self._database_health_check())
        )
        
        logger.info(f"Started {len(self.tasks)} periodic tasks")
    
    async def stop(self):
        """Stop all periodic tasks."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping periodic tasks...")
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("All periodic tasks stopped")
    
    async def _cleanup_expired_states(self):
        """Clean up expired admin states every hour."""
        while self.running:
            try:
                # Import here to avoid circular imports
                from handlers.admin_states import cleanup_expired_states
                
                logger.debug("Running expired states cleanup...")
                cleanup_expired_states()
                
                # Run every hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                # Wait 5 minutes before retry
                await asyncio.sleep(300)
    
    async def _database_health_check(self):
        """Check database health every 5 minutes."""
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
    """Start all periodic tasks."""
    await periodic_task_manager.start()


async def stop_periodic_tasks():
    """Stop all periodic tasks."""
    await periodic_task_manager.stop()