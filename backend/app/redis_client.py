import os
import redis

def get_redis() -> redis.Redis:
  
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis.from_url(redis_url, decode_responses=True)

 
    host = os.getenv("REDISHOST") or os.getenv("REDIS_HOST") or "localhost"
    port = int(os.getenv("REDISPORT") or os.getenv("REDIS_PORT") or 6379)
    db = int(os.getenv("REDIS_DB", 0))
    password = os.getenv("REDISPASSWORD") or os.getenv("REDIS_PASSWORD") or None

    return redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        decode_responses=True
    )