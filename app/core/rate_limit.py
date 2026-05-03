# app/core/rate_limit.py
import logging
import time

import redis

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

def check_rate_limit(user_id: int, limit: int = 5, period: int = 60) -> bool:
    key = f"rl:{user_id}"
    now = int(time.time())
    try:
        pipeline = redis_client.pipeline()
        pipeline.zremrangebyscore(key, 0, now - period)
        pipeline.zcard(key)
        _, count = pipeline.execute()

        if count >= limit:
            return False

        redis_client.zadd(key, {str(now): now})
        redis_client.expire(key, period + 2)
        return True
    except redis.RedisError as exc:
        logger.warning("Rate-limit backend unavailable for user %s: %s", user_id, exc)
        return True