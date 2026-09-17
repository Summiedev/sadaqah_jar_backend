import json
import logging
from datetime import date, datetime
from enum import Enum

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    socket_connect_timeout=2,
    socket_timeout=2,
    max_connections=getattr(settings, "REDIS_MAX_CONNECTIONS", 50),
    health_check_interval=30,
    retry_on_timeout=True,
)


def _json_default(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def test_redis():
    try:
        redis_client.set("ping", "pong")
        print(redis_client.get("ping"))
    except redis.RedisError as exc:
        logger.warning("Redis ping failed: %s", exc)


def cache_daily_acts(user_id: int, acts: list, ttl=86400):
    key = f"daily_acts:{user_id}"
    try:
        redis_client.set(key, json.dumps(acts, default=_json_default), ex=ttl)
    except redis.RedisError as exc:
        logger.warning("Failed to cache daily acts for user %s: %s", user_id, exc)


def get_cached_daily_acts(user_id: int):
    key = f"daily_acts:{user_id}"
    try:
        acts = redis_client.get(key)
    except redis.RedisError as exc:
        logger.warning("Failed to read cached daily acts for user %s: %s", user_id, exc)
        return None

    if acts:
        try:
            return json.loads(acts.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Invalid cached daily acts for user %s: %s", user_id, exc)
            try:
                redis_client.delete(key)
            except redis.RedisError:
                pass
    return None


def cache_user_streak(user_id: int, streak_data: dict, ttl=3600):
    key = f"streak:{user_id}"
    try:
        redis_client.set(key, json.dumps(streak_data, default=_json_default), ex=ttl)
    except redis.RedisError as exc:
        logger.warning("Failed to cache streak for user %s: %s", user_id, exc)


def get_cached_user_streak(user_id: int):
    key = f"streak:{user_id}"
    try:
        data = redis_client.get(key)
    except redis.RedisError as exc:
        logger.warning("Failed to read streak cache for user %s: %s", user_id, exc)
        return None

    if data:
        try:
            return json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("Invalid streak cache for user %s: %s", user_id, exc)
            try:
                redis_client.delete(key)
            except redis.RedisError:
                pass
    return None


def cache_dashboard_stats(user_id: int, stats: dict, ttl=300):
    key = f"dashboard:stats:{user_id}"
    try:
        redis_client.set(key, json.dumps(stats, default=_json_default), ex=ttl)
    except redis.RedisError as exc:
        logger.warning("Failed to cache dashboard stats for user %s: %s", user_id, exc)


def get_cached_dashboard_stats(user_id: int):
    key = f"dashboard:stats:{user_id}"
    try:
        data = redis_client.get(key)
    except redis.RedisError as exc:
        logger.warning(
            "Failed to read dashboard stats cache for user %s: %s", user_id, exc
        )
        return None
    if data:
        try:
            return json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Invalid dashboard stats cache for user %s: %s", user_id, exc
            )
            try:
                redis_client.delete(key)
            except redis.RedisError:
                pass
    return None


def cache_category_analytics(user_id: int, data: list, ttl=300):
    key = f"dashboard:category:{user_id}"
    try:
        redis_client.set(key, json.dumps(data, default=_json_default), ex=ttl)
    except redis.RedisError as exc:
        logger.warning(
            "Failed to cache category analytics for user %s: %s", user_id, exc
        )


def get_cached_category_analytics(user_id: int):
    key = f"dashboard:category:{user_id}"
    try:
        data = redis_client.get(key)
    except redis.RedisError as exc:
        logger.warning(
            "Failed to read category analytics cache for user %s: %s", user_id, exc
        )
        return None
    if data:
        try:
            return json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Invalid category analytics cache for user %s: %s", user_id, exc
            )
            try:
                redis_client.delete(key)
            except redis.RedisError:
                pass
    return None


def cache_json(key: str, value, *, ttl: int) -> None:
    """Best-effort JSON cache shared by read-only catalogue endpoints."""
    try:
        redis_client.set(key, json.dumps(value, default=_json_default), ex=ttl)
    except redis.RedisError as exc:
        logger.warning("Failed to write cache key %s: %s", key, exc)


def get_cached_json(key: str):
    """Return cached JSON, preserving valid falsey values such as ``[]``."""
    try:
        value = redis_client.get(key)
    except redis.RedisError as exc:
        logger.warning("Failed to read cache key %s: %s", key, exc)
        return None
    if value is None:
        return None
    try:
        return json.loads(value.decode("utf-8") if isinstance(value, bytes) else value)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        logger.warning("Invalid JSON cache key %s: %s", key, exc)
        try:
            redis_client.delete(key)
        except redis.RedisError:
            pass
        return None


def invalidate_cache_pattern(pattern: str) -> None:
    """Delete matching keys without blocking Redis with the KEYS command."""
    try:
        keys = list(redis_client.scan_iter(match=pattern, count=100))
        if keys:
            redis_client.delete(*keys)
    except redis.RedisError as exc:
        logger.warning("Failed to invalidate cache pattern %s: %s", pattern, exc)
