import asyncio
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db import init_db


async def main():
    await init_db()
    print("DB initialized OK")


if __name__ == "__main__":
    asyncio.run(main())
