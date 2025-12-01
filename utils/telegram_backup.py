"""Telegram backup system with ZIP archives and automatic delivery."""

import os
import shutil
import sqlite3
import tempfile
import zipfile
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from aiogram import Bot
from aiogram.types import BufferedInputFile
from config import LOG_FILE_PATH, TOKEN, BACKUP_RECIPIENT_ID
from utils.time_helper import format_admin_time
from models.database import DB_PATH
from utils.logging_setup import get_logger

logger = get_logger(__name__)


class BackupManager:
    """Manages backup creation and Telegram delivery."""

    def __init__(self, db_path=None, log_file_path=None, backup_dir="./data/backups"):
        self.db_path = db_path or str(DB_PATH)
        self.log_file_path = log_file_path or LOG_FILE_PATH
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.keep_local_backups = 3

    async def create_backup(self):
        """Create complete backup archive with metadata."""
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(
                    f"Database file {self.db_path} not found!")

            with tempfile.TemporaryDirectory() as tmp_dir:
                timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
                backup_path = os.path.join(tmp_dir, f"backup_{timestamp}.db")
                zip_filename = f"bot_backup_{timestamp}.zip"
                zip_path = os.path.join(tmp_dir, zip_filename)

                # Copy database using SQLite backup method
                conn = sqlite3.connect(self.db_path)
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
                conn.close()

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    zipf.write(backup_path, "database.db")
                    db_size = os.path.getsize(backup_path)

                    self._add_log_excerpt(zipf)
                    zipf.writestr("backup_info.txt",
                                  self._create_backup_info(db_size))

                zip_size = os.path.getsize(zip_path)
                if zip_size > 50 * 1024 * 1024:
                    logger.warning(
                        f"Backup too large for Telegram: {zip_size} bytes")
                    return None, None, 0

                self._save_local_copy(zip_path, zip_filename)

                with open(zip_path, 'rb') as f:
                    backup_data = f.read()

                logger.info(
                    f"Backup created: {zip_filename} ({zip_size} bytes)")
                return backup_data, zip_filename, zip_size

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None, None, 0

    def _add_log_excerpt(self, zipf: zipfile.ZipFile):
        """Add last 100KB of logs to archive."""
        try:
            if not os.path.exists(self.log_file_path):
                return

            with open(self.log_file_path, 'rb') as f:
                f.seek(0, 2)
                file_size = f.tell()
                if file_size > 100 * 1024:
                    f.seek(-100 * 1024, 2)
                else:
                    f.seek(0)
                zipf.writestr("recent_logs.log", f.read())
        except Exception as e:
            logger.warning(f"Failed to add log excerpt: {e}")

    def _create_backup_info(self, db_size: int) -> str:
        """Create backup metadata file."""
        try:
            db_stats = self._get_database_stats()
            created_at = format_admin_time(
                datetime.utcnow(), "%d.%m.%Y %H:%M:%S")
            return f""" Bot Backup Information
Created: {created_at}
Database: {os.path.basename(self.db_path)}
Database Size: {db_size:,} bytes ({db_size / 1024 / 1024:.2f} MB)

Database Statistics:
{db_stats}

Keep this backup file safe!
"""
        except Exception as e:
            return f"Backup created: {format_admin_time(datetime.utcnow())}\nError: {e}"

    def _get_database_stats(self) -> str:
        """Get table statistics from database."""
        try:
            stats = []
            with sqlite3.connect(self.db_path) as conn:
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                for (table,) in tables:
                    try:
                        count = conn.execute(
                            f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                        stats.append(f"• {table}: {count:,} records")
                    except Exception:
                        stats.append(f"• {table}: unable to count")
            return "\n".join(stats) if stats else "No tables found"
        except Exception as e:
            return f"Unable to get stats: {e}"

    def _save_local_copy(self, zip_path: str, zip_filename: str):
        """Save local backup copy with rotation."""
        try:
            shutil.copy2(zip_path, self.backup_dir / zip_filename)
            self._cleanup_old_backups()
        except Exception as e:
            logger.warning(f"Failed to save local backup: {e}")

    def _cleanup_old_backups(self):
        """Delete old backups, keep last N."""
        try:
            backups = sorted(
                self.backup_dir.glob("bot_backup_*.zip"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            for old in backups[self.keep_local_backups:]:
                old.unlink()
                logger.debug(f"Removed old backup: {old.name}")
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

    def _format_size(self, size: int) -> str:

        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    async def send_backup(self, user_id=None, bot_instance=None):
        """Send backup to admin or specified user."""
        bot = None
        created_bot = False

        try:
            if bot_instance:
                bot = bot_instance
            else:
                bot = Bot(token=TOKEN)
                created_bot = True

            backup_data, filename, file_size = await self.create_backup()
            if not backup_data:
                raise Exception("Failed to create backup!")

            recipient_id = user_id or BACKUP_RECIPIENT_ID
            caption = f"""🔄 Bot backup

📁 File: {filename}
📊 Size: {self._format_size(file_size)}
📅 Created: {format_admin_time(datetime.utcnow())} """

            await bot.send_document(
                chat_id=recipient_id,
                document=BufferedInputFile(backup_data, filename=filename),
                caption=caption
            )

            logger.info(f"Backup sent to user {recipient_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending backup: {e}")
            return False
        finally:
            if created_bot and bot:
                try:
                    await bot.session.close()
                except Exception:
                    pass


backup_manager = BackupManager()


async def create_and_send_backup(recipient_id: int, bot_instance=None) -> bool:
    """Create and send backup to specified user."""
    return await backup_manager.send_backup(user_id=recipient_id, bot_instance=bot_instance)


async def scheduled_backup_task(recipient_id: int):
    """Execute scheduled backup."""
    logger.info(f"Running scheduled backup for user {recipient_id}...")
    try:
        success = await create_and_send_backup(recipient_id)
        if success:
            logger.info("Scheduled backup completed")
        else:
            logger.error("Scheduled backup failed")
    except Exception as e:
        logger.error(f"Error in scheduled backup: {e}")


async def backup_scheduler_task(recipient_id: int):
    """Background task for daily backups."""
    logger.info(f"Backup scheduler started for user {recipient_id}")

    while True:
        try:
            await asyncio.sleep(24 * 3600)
            await scheduled_backup_task(recipient_id)
        except asyncio.CancelledError:
            logger.info("Backup scheduler cancelled")
            break
        except Exception as e:
            logger.error(f"Error in backup scheduler: {e}")
            await asyncio.sleep(3600)
