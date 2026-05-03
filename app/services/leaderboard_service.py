from app.core.cache import redis_client
from datetime import datetime

GLOBAL_KEY = "leaderboard:global"
RAMADAN_KEY = "leaderboard:ramadan"

def increment_global(user_id: int, stars: int):
    redis_client.zincrby(GLOBAL_KEY, stars, user_id)

def increment_ramadan(user_id: int, stars: int):
    redis_client.zincrby(RAMADAN_KEY, stars, user_id)

def get_top_global(limit: int = 10):
    return redis_client.zrevrange(GLOBAL_KEY, 0, limit - 1, withscores=True)

def get_top_ramadan(limit: int = 10):
    return redis_client.zrevrange(RAMADAN_KEY, 0, limit - 1, withscores=True)
def get_week_key():
    now = datetime.utcnow()
    year, week, _ = now.isocalendar()
    return f"leaderboard:week:{year}-{week}"

def increment_weekly(user_id: int, stars: int):
    redis_client.zincrby(get_week_key(), stars, user_id)

def get_top_weekly(limit: int = 10):
    return redis_client.zrevrange(get_week_key(), 0, limit - 1, withscores=True)

def get_user_rank_global(user_id: int):
    rank = redis_client.zrevrank(GLOBAL_KEY, user_id)
    if rank is None:
        return None
    
    score = redis_client.zscore(GLOBAL_KEY, user_id)
    
    return {
        "rank": rank + 1,  # Redis is 0-indexed
        "score": int(score)
    }


def get_user_rank_ramadan(user_id: int):
    rank = redis_client.zrevrank(RAMADAN_KEY, user_id)
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
    redis_client.zincrby(get_family_key(jar_id), stars, user_id)

def get_top_family(jar_id: int, limit: int = 10):
    return redis_client.zrevrange(get_family_key(jar_id), 0, limit - 1, withscores=True)

FRIDAY_KEY = "leaderboard:friday"

def increment_friday(user_id: int, stars: int):
    redis_client.zincrby(FRIDAY_KEY, stars, user_id)

def get_top_friday(limit: int = 10):
    return redis_client.zrevrange(FRIDAY_KEY, 0, limit - 1, withscores=True)

# Week key expiration: 21 days (3 weeks) to be safe
def ensure_week_key_expires():
    key = get_week_key()
    if not redis_client.exists(key):
        redis_client.zadd(key, {})  # ensure key exists
    redis_client.expire(key, 21 * 24 * 3600)