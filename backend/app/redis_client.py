import os
import redis
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB


def get_redis() -> redis.Redis:
    
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.from_url(redis_url, decode_responses=True)

    host = os.getenv("REDISHOST") or os.getenv("REDIS_HOST") or REDIS_HOST or "localhost"
    port = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT") or REDIS_PORT or 6379)
    db = int(os.getenv("REDIS_DB") or REDIS_DB or 0)

    pool = redis.ConnectionPool(
        host=host, port=port, db=db, decode_responses=True
    )
    return redis.Redis(connection_pool=pool)