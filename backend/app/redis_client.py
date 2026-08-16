import redis

from .config import REDIS_HOST, REDIS_PORT, REDIS_DB

redis_pool = redis.ConnectionPool(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=redis_pool)
