import redis
import json

from app.core.config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL)

def test_redis():
    redis_client.set("ping", "pong")
    print(redis_client.get("ping"))
    
def cache_daily_acts(user_id: int, acts: list, ttl=86400):
    key = f"daily_acts:{user_id}"
    redis_client.set(key, json.dumps(acts), ex=ttl)

def get_cached_daily_acts(user_id: int):
    key = f"daily_acts:{user_id}"
    acts = redis_client.get(key)
    if acts:
        return json.loads(acts.decode("utf-8"))
    return None

def cache_user_streak(user_id: int, streak_data: dict, ttl=3600):
    key = f"streak:{user_id}"
    redis_client.set(key, json.dumps(streak_data), ex=ttl)


def get_cached_user_streak(user_id: int):
    key = f"streak:{user_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return None