import orjson
from pathlib import Path

CACHE_PATH = Path("data/cache.json")

def load_cache():
    if not CACHE_PATH.exists():
        return {}
    return orjson.loads(CACHE_PATH.read_bytes())

def save_cache(data):
    CACHE_PATH.write_bytes(orjson.dumps(data))
