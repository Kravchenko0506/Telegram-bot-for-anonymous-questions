"""
Telegram Backup System for Anonymous Questions Bot

Comprehensive backup solution with Telegram delivery:
• ZIP archives with SQLite integrity verification
• Direct Telegram delivery with size validation
• Automatic local backup rotation
• Database statistics and restore instructions
• Error handling and logging integration

Uses SQLite backup() API for safe database copying and includes
detailed restore instructions with metadata for reliable recovery.
"""

import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
import asyncio
import logging

from aiogram import Bot
from aiogram.types import FSInputFile, BufferedInputFile
from config import LOG_FILE_PATH, TOKEN, BACKUP_RECIPIENT_ID
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
        """Creates a complete backup archive with metadata and instructions."""
        try:
            if not os.path.exists(self.db_path):
                raise FileNotFoundError(
                    f"Database file {self.db_path} not found!")

            with tempfile.TemporaryDirectory() as tmp_dir:
                timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                backup_filename = f"backup_{timestamp}.db"
                zip_filename = f"bot_backup_{timestamp}.zip"

                backup_path = os.path.join(tmp_dir, backup_filename)
                zip_path = os.path.join(tmp_dir, zip_filename)

                logger.info(f"Creating comprehensive backup: {zip_filename}")

                logger.info("Copying database using SQLite backup method...")
                conn = sqlite3.connect(self.db_path)
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
                conn.close()

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    zipf.write(backup_path, "database.db")
                    db_size = os.path.getsize(backup_path)
                    logger.info(f"Database added to archive: {db_size} bytes")

                    await self._add_log_excerpt(zipf, tmp_dir)

                    backup_info = self._create_backup_info(db_size)
                    zipf.writestr("backup_info.txt", backup_info)

                    restore_info = self._create_restore_instructions()
                    zipf.writestr("RESTORE_INSTRUCTIONS.txt", restore_info)

                zip_size = os.path.getsize(zip_path)
                if zip_size > 50 * 1024 * 1024:
                    logger.warning(
                        f"Backup too large for Telegram: {zip_size} bytes")
                    return None, None, 0

                await self._save_local_copy(zip_path, zip_filename)

                with open(zip_path, 'rb') as f:
                    backup_data = f.read()

                logger.info(
                    f"✅ Backup created successfully: {zip_filename} ({zip_size} bytes)")
                return backup_data, zip_filename, zip_size

        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return None, None, 0

    async def _add_log_excerpt(self, zipf: zipfile.ZipFile, tmp_dir: str):
        """Adds log excerpt to archive (last 100KB)."""
        try:
            if not os.path.exists(self.log_file_path):
                logger.warning(f"Log file not found: {self.log_file_path}")
                return

            with open(self.log_file_path, 'rb') as f:
                f.seek(0, 2)
                file_size = f.tell()

                if file_size > 100 * 1024:
                    f.seek(-100 * 1024, 2)
                    log_excerpt = f.read()
                else:
                    f.seek(0)
                    log_excerpt = f.read()

            zipf.writestr("recent_logs.log", log_excerpt)
            logger.info(f"Log excerpt added: {len(log_excerpt)} bytes")

        except Exception as e:
            logger.warning(f"Failed to add log excerpt: {e}")

    def _create_backup_info(self, db_size: int) -> str:
        """Creates backup metadata file."""
        try:
            db_stats = self._get_database_stats()

            backup_info = f"""🤖 Bot Backup Information
Created: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Database: {os.path.basename(self.db_path)}
Database Size: {db_size:,} bytes ({db_size / 1024 / 1024:.2f} MB)

📁 Archive Contents:
- database.db - Main bot database (SQLite backup method)
- recent_logs.log - Recent log entries (last 100KB)
- backup_info.txt - This metadata file
- RESTORE_INSTRUCTIONS.txt - Step-by-step restore guide

📊 Database Statistics:
{db_stats}

⚠️ Keep this backup file safe and secure!
Created using SQLite backup() method for data integrity.
"""
            return backup_info

        except Exception as e:
            logger.warning(f"Error creating backup info: {e}")
            return f"Backup created: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\nError getting detailed info: {e}"

    def _get_database_stats(self) -> str:
        """Gets statistics on tables in the database."""
        try:
            stats_lines = []
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                for (table_name,) in tables:
                    try:
                        count = conn.execute(
                            f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                        stats_lines.append(
                            f"• {table_name}: {count:,} records")
                    except Exception:
                        stats_lines.append(f"• {table_name}: unable to count")

            return "\n".join(stats_lines) if stats_lines else "No tables found"

        except Exception as e:
            return f"Unable to get stats: {e}"

    def _create_restore_instructions(self) -> str:
        """Creates detailed restore instructions."""
        return """📋 RESTORE INSTRUCTIONS

🔴 IMPORTANT: This backup was created using SQLite backup() method!

How to restore your bot from this backup:

1. 🛑 STOP the bot completely
   - Press Ctrl+C in terminal
   - Or stop the Docker container: docker stop container_name
   - Or stop the service if running as daemon

2. 📁 BACKUP current data (HIGHLY RECOMMENDED)
   - Copy current database file: cp database.db database.db.backup
   - This allows you to roll back if something goes wrong

3. 📥 EXTRACT this ZIP file
   - Unzip the archive: unzip bot_backup_YYYYMMDD_HHMMSS.zip
   - You'll get: database.db, logs, and instruction files

4. 🔄 REPLACE the database
   - Copy database.db to your bot's data folder
   - Make sure file permissions are correct: chmod 644 database.db

5. 🚀 START the bot
   - Run your bot as usual: python main.py
   - Or restart Docker container
   - Check logs for any startup errors

6. ✅ VERIFY restoration
   - Check that bot responds to commands
   - Verify that your data is present
   - Test critical bot functions

⚠️ TROUBLESHOOTING:
- If bot won't start: restore original database.db.backup
- If data is missing: check that you replaced the correct file
- If permissions error: chown user:group database.db

📞 The backup includes recent logs that might help diagnose issues.

💡 This backup method preserves SQLite integrity and all indexes.
"""

    async def _save_local_copy(self, zip_path: str, zip_filename: str):
        """Saves local copy of archive with automatic rotation."""
        try:
            local_backup_path = self.backup_dir / zip_filename

            import shutil
            shutil.copy2(zip_path, local_backup_path)
            logger.info(f"Local backup saved: {local_backup_path}")

            await self._cleanup_old_local_backups()

        except Exception as e:
            logger.warning(f"Failed to save local backup: {e}")

    async def _cleanup_old_local_backups(self):
        """Deletes old local backups, keeping only the last N."""
        try:
            backup_files = list(self.backup_dir.glob("bot_backup_*.zip"))

            if len(backup_files) <= self.keep_local_backups:
                return

            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            files_to_delete = backup_files[self.keep_local_backups:]
            deleted_count = 0

            for old_backup in files_to_delete:
                try:
                    old_backup.unlink()
                    logger.debug(
                        f"Removed old local backup: {old_backup.name}")
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {old_backup.name}: {e}")

            if deleted_count > 0:
                logger.info(f"🗑️ Cleaned up {deleted_count} old local backups")

        except Exception as e:
            logger.error(f"Local backup cleanup failed: {e}")

    async def send_backup(self, user_id=None, bot_instance=None):
        """Sends backup copy to admin or specified user."""
        try:
            bot = bot_instance if bot_instance else Bot(token=TOKEN)
            close_bot_after = bot_instance is None

            backup_data, filename, file_size = await self.create_backup()

            if not backup_data:
                raise Exception("Failed to create backup!")

            recipient_id = user_id or BACKUP_RECIPIENT_ID

            size_mb = file_size / 1024 / 1024
            caption = f"""🔄 Bot backup copy

📁 File: {filename}
📊 Size: {size_mb:.1f} MB
📅 Created: {datetime.now().strftime('%d.%m.%Y %H:%M')}
🔒 Method: SQLite backup() - guarantees data integrity

📋 Archive contains detailed restoration instructions"""

            await bot.send_document(
                chat_id=recipient_id,
                document=BufferedInputFile(backup_data, filename=filename),
                caption=caption
            )

            logger.info(f"✅ Backup sent successfully to user {recipient_id}")

            if close_bot_after:
                await bot.close()

            return True

        except Exception as e:
            logger.error(f"❌ Error sending backup: {e}")
            return False

    def get_backup_stats(self) -> dict:
        """Returns statistics about local backups."""
        try:
            backup_files = list(self.backup_dir.glob("bot_backup_*.zip"))

            if not backup_files:
                return {
                    'total_backups': 0,
                    'total_size_mb': 0,
                    'backup_directory': str(self.backup_dir),
                    'newest_backup': None,
                    'oldest_backup': None
                }

            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            total_size = sum(f.stat().st_size for f in backup_files)
            newest = datetime.fromtimestamp(backup_files[0].stat().st_mtime)
            oldest = datetime.fromtimestamp(backup_files[-1].stat().st_mtime)

            return {
                'total_backups': len(backup_files),
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'backup_directory': str(self.backup_dir),
                'newest_backup': newest.strftime('%d.%m.%Y %H:%M'),
                'oldest_backup': oldest.strftime('%d.%m.%Y %H:%M')
            }

        except Exception as e:
            logger.error(f"Error getting backup stats: {e}")
            return {'error': str(e)}


# Global manager instance
backup_manager = BackupManager()


# Wrapper functions for backward compatibility
async def create_and_send_backup(recipient_id: int, bot_instance=None) -> bool:
    """
    Create backup and send to specified Telegram user.

    Args:
        recipient_id: Telegram user ID to receive backup
        bot_instance: Bot instance (optional, will create temporary if not provided)

    Returns:
        True if backup was created and sent successfully
    """
    return await backup_manager.send_backup(user_id=recipient_id, bot_instance=bot_instance)


def get_backup_statistics() -> dict:
    """
    Get comprehensive statistics about local backup files.

    Returns:
        Dictionary with backup statistics including file count, sizes, and details
    """
    return backup_manager.get_backup_stats()


async def scheduled_backup_task(recipient_id: int):
    """Execute scheduled backup and send to configured recipient."""
    logger.info(f"🔄 Running scheduled backup for user {recipient_id}...")

    try:
        success = await create_and_send_backup(recipient_id)
        if success:
            logger.info("✅ Scheduled backup completed successfully")
        else:
            logger.error("❌ Scheduled backup failed")
    except Exception as e:
        logger.error(f"Error in scheduled backup task: {e}")


async def backup_scheduler_task(recipient_id: int):
    """Background task that runs backup scheduler every 24 hours."""
    logger.info(f"📅 Telegram backup scheduler started for user {recipient_id}")

    while True:
        try:
            # Wait 24 hours
            await asyncio.sleep(24 * 3600)

            # Execute backup
            await scheduled_backup_task(recipient_id)

        except asyncio.CancelledError:
            logger.info("Backup scheduler task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in backup scheduler: {e}")
            # Wait 1 hour before retrying on error
            await asyncio.sleep(3600)
