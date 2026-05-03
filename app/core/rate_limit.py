# app/core/rate_limit.py
import time
from app.core.cache import redis_client

def check_rate_limit(user_id: int, limit: int = 5, period: int = 60) -> bool:
    key = f"rl:{user_id}"
    now = int(time.time())
    pipeline = redis_client.pipeline()
    pipeline.zremrangebyscore(key, 0, now - period)
    pipeline.zcard(key)
    _, count = pipeline.execute()

    if count >= limit:
        return False

    redis_client.zadd(key, {str(now): now})
    redis_client.expire(key, period + 2)
    return True