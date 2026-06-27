# app/core/rate_limit.py
import logging
import time
import uuid

import redis

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

def check_rate_limit_key(key: str, limit: int = 5, period: int = 60) -> bool:
    now = int(time.time())
    member = f"{now}:{uuid.uuid4().hex}"
    try:
        pipeline = redis_client.pipeline()
        pipeline.zremrangebyscore(key, 0, now - period)
        pipeline.zcard(key)
        _, count = pipeline.execute()

        if count >= limit:
            return False

        redis_client.zadd(key, {member: now})
        redis_client.expire(key, period + 2)
        return True
    except redis.RedisError as exc:
        logger.warning("Rate-limit backend unavailable for key %s: %s", key, exc)
        return True


def check_rate_limit(user_id: int, limit: int = 5, period: int = 60) -> bool:
    return check_rate_limit_key(f"rl:{user_id}", limit=limit, period=period)