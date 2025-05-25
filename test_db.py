import asyncio
import asyncpg


async def main():
    conn = await asyncpg.connect(
        user="botanon",
        password="BotDB25052025",
        database="dbfrombot",
        host="127.0.0.1"
    )
    result = await conn.fetch('SELECT 1;')
    print(result)
    await conn.close()

asyncio.run(main())
