import sys
import asyncio

# asyncpg + pytest on Windows is more stable with SelectorEventLoopPolicy.
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
