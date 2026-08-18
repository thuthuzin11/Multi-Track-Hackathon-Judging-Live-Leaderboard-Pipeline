import os
import redis
from .config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD


def get_redis() -> redis.Redis:
    # 1. REDIS_URL (For Railway / Cloud deployment)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.from_url(redis_url, decode_responses=True)

    # 2. Environment Variables or Config fallback
    host = os.getenv("REDISHOST") or os.getenv("REDIS_HOST") or REDIS_HOST or "localhost"
    port = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT") or REDIS_PORT or 6379)
    db = int(os.getenv("REDIS_DB") or REDIS_DB or 0)
    
    # Password ကို Railway variable (REDISPASSWORD / REDIS_PASSWORD) သို့မဟုတ် config မှ ယူခြင်း
    password = os.getenv("REDISPASSWORD") or os.getenv("REDIS_PASSWORD") or REDIS_PASSWORD or None

    pool = redis.ConnectionPool(
        host=host, port=port, db=db, password=password, decode_responses=True
    )
    return redis.Redis(connection_pool=pool)