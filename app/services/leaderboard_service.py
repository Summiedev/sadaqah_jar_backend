import logging
from app.core.cache import redis_client
from datetime import datetime
import redis

logger = logging.getLogger(__name__)

GLOBAL_KEY = "leaderboard:global"
RAMADAN_KEY = "leaderboard:ramadan"

def increment_global(user_id: int, stars: int):
    try:
        redis_client.zincrby(GLOBAL_KEY, stars, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to increment global leaderboard for user %s: %s", user_id, exc)

def increment_ramadan(user_id: int, stars: int):
    try:
        redis_client.zincrby(RAMADAN_KEY, stars, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to increment ramadan leaderboard for user %s: %s", user_id, exc)

def get_top_global(limit: int = 10):
    try:
        return redis_client.zrevrange(GLOBAL_KEY, 0, limit - 1, withscores=True)
    except redis.RedisError as exc:
        logger.warning("Failed to read global leaderboard: %s", exc)
        return []

def get_top_ramadan(limit: int = 10):
    try:
        return redis_client.zrevrange(RAMADAN_KEY, 0, limit - 1, withscores=True)
    except redis.RedisError as exc:
        logger.warning("Failed to read ramadan leaderboard: %s", exc)
        return []
def get_week_key():
    now = datetime.utcnow()
    year, week, _ = now.isocalendar()
    return f"leaderboard:week:{year}-{week}"

def increment_weekly(user_id: int, stars: int):
    try:
        redis_client.zincrby(get_week_key(), stars, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to increment weekly leaderboard for user %s: %s", user_id, exc)

def get_top_weekly(limit: int = 10):
    try:
        return redis_client.zrevrange(get_week_key(), 0, limit - 1, withscores=True)
    except redis.RedisError as exc:
        logger.warning("Failed to read weekly leaderboard: %s", exc)
        return []

def get_user_rank_global(user_id: int):
    try:
        rank = redis_client.zrevrank(GLOBAL_KEY, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to read global rank for user %s: %s", user_id, exc)
        return None
    if rank is None:
        return None
    
    score = redis_client.zscore(GLOBAL_KEY, user_id)
    
    return {
        "rank": rank + 1,  # Redis is 0-indexed
        "score": int(score)
    }


def get_user_rank_ramadan(user_id: int):
    try:
        rank = redis_client.zrevrank(RAMADAN_KEY, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to read ramadan rank for user %s: %s", user_id, exc)
        return None
    if rank is None:
        return None

    score = redis_client.zscore(RAMADAN_KEY, user_id)

    return {
        "rank": rank + 1,
        "score": int(score)
    }
    

def get_family_key(jar_id: int):
    return f"leaderboard:family:{jar_id}"

def increment_family_leaderboard(jar_id: int, user_id: int, stars: int):
    try:
        redis_client.zincrby(get_family_key(jar_id), stars, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to increment family leaderboard for jar %s user %s: %s", jar_id, user_id, exc)

def get_top_family(jar_id: int, limit: int = 10):
    try:
        return redis_client.zrevrange(get_family_key(jar_id), 0, limit - 1, withscores=True)
    except redis.RedisError as exc:
        logger.warning("Failed to read family leaderboard for jar %s: %s", jar_id, exc)
        return []

FRIDAY_KEY = "leaderboard:friday"

def increment_friday(user_id: int, stars: int):
    try:
        redis_client.zincrby(FRIDAY_KEY, stars, user_id)
    except redis.RedisError as exc:
        logger.warning("Failed to increment friday leaderboard for user %s: %s", user_id, exc)

def get_top_friday(limit: int = 10):
    try:
        return redis_client.zrevrange(FRIDAY_KEY, 0, limit - 1, withscores=True)
    except redis.RedisError as exc:
        logger.warning("Failed to read friday leaderboard: %s", exc)
        return []

# Week key expiration: 21 days (3 weeks) to be safe
def ensure_week_key_expires():
    key = get_week_key()
    try:
        if not redis_client.exists(key):
            redis_client.zadd(key, {})  # ensure key exists
        redis_client.expire(key, 21 * 24 * 3600)
    except redis.RedisError as exc:
        logger.warning("Failed to set weekly leaderboard expiry: %s", exc)