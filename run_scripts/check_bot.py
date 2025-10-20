import asyncio
from dotenv import load_dotenv
from aiogram import Bot
import os


async def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN is missing in .env")
    async with Bot(token) as bot:
        me = await bot.get_me()
        print(f"OK: bot @{me.username} (id={me.id})")


if __name__ == "__main__":
    asyncio.run(main())
