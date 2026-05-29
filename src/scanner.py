import asyncio
import random
import uvloop
import aiofiles
import orjson
from pathlib import Path
from tls_probe import probe
from domains import DOMAINS, PORTS
from cache import load_cache, save_cache

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

DATA_DIR = Path("data")
RESULTS_FILE = DATA_DIR / "results.json"

SEM = asyncio.Semaphore(500)

async def read_ips():
    async with aiofiles.open(DATA_DIR / "ips.txt", "r") as f:
        return [x.strip() for x in await f.readlines() if x.strip()]

async def test_ip(ip, port, cache):
    async with SEM:
        domains = DOMAINS[:]
        random.shuffle(domains)

        for domain in domains:
            result = await probe(ip, port, domain)

            if result["ok"]:
                key = f"{ip}:{port}"

                cache[key] = {
                    "latency": result["latency"],
                    "sni": result["sni"]
                }

                return {
                    "ip": ip,
                    "port": port,
                    "latency": result["latency"],
                    "sni": result["sni"]
                }

        return None

async def main():
    cache = load_cache()

    ips = await read_ips()

    cached_ips = []
    new_ips = []

    for ip in ips:
        found = False

        for port in PORTS:
            if f"{ip}:{port}" in cache:
                cached_ips.append(ip)
                found = True
                break

        if not found:
            new_ips.append(ip)

    ordered_ips = list(dict.fromkeys(cached_ips + new_ips))

    tasks = []

    for ip in ordered_ips:
        for port in PORTS:
            tasks.append(test_ip(ip, port, cache))

    results = await asyncio.gather(*tasks)

    valid = [x for x in results if x]

    final = {}

    for port in PORTS:
        items = [x for x in valid if x["port"] == port]
        items.sort(key=lambda x: x["latency"])
        final[str(port)] = items[:10]

    RESULTS_FILE.write_bytes(orjson.dumps(final))

    save_cache(cache)

asyncio.run(main())
