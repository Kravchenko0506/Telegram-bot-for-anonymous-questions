"""
Debug script to check bot configuration and database connection
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_database():
    """Check PostgreSQL connection."""
    try:
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER", "botanon"),
            password=os.getenv("DB_PASSWORD", "BotDB25052025"),
            database=os.getenv("DB_NAME", "dbfrombot"),
            host=os.getenv("DB_HOST", "127.0.0.1")
        )
        result = await conn.fetch('SELECT 1;')
        print("✅ Database connection successful")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def check_bot_token():
    """Check if bot token is valid."""
    from aiogram import Bot
    
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN not found in .env file")
        return False
    
    try:
        bot = Bot(token=token)
        bot_info = await bot.get_me()
        print(f"✅ Bot token valid: @{bot_info.username}")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"❌ Bot token invalid: {e}")
        return False


def check_config_file():
    """Check if all required variables are in .env."""
    required_vars = [
        "BOT_TOKEN",
        "ADMIN_ID",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing variables in .env: {missing}")
        return False
    else:
        print("✅ All required variables found in .env")
        return True


async def main():
    """Run all diagnostic checks."""
    print("🔍 Checking bot configuration...\n")
    
    # Check .env file
    env_ok = check_config_file()
    
    # Check database
    db_ok = await check_database()
    
    # Check bot token
    bot_ok = await check_bot_token()
    
    print(f"\n📊 Results:")
    print(f"Config file: {'✅' if env_ok else '❌'}")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Bot token: {'✅' if bot_ok else '❌'}")
    
    if all([env_ok, db_ok, bot_ok]):
        print("\n🎉 All checks passed! Bot should work.")
    else:
        print("\n⚠️ Fix the issues above before running the bot.")


if __name__ == "__main__":
    asyncio.run(main())