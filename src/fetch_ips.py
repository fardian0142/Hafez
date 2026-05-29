import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from domains import IP_SOURCES

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

OUTPUT = DATA_DIR / "ips.txt"

async def fetch(session, url):
    async with session.get(url, timeout=30) as r:
        return await r.text()

async def main():
    ips = set()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in IP_SOURCES]
        results = await asyncio.gather(*tasks)

    for text in results:
        for line in text.splitlines():
            line = line.strip()
            if line:
                ips.add(line)

    async with aiofiles.open(OUTPUT, "w") as f:
        await f.write("\n".join(sorted(ips)))

asyncio.run(main())
