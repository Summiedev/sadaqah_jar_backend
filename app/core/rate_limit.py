# app/core/rate_limit.py
import logging
import time
import uuid

import redis

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

# Atomic sliding-window limiter. Runs entirely inside Redis so the
# prune -> count -> (maybe) add sequence cannot interleave across
# concurrent callers (fixes the check-then-act race where N concurrent
# requests could all read count < limit before any of them added).
#
# KEYS[1] = the rate-limit key
# ARGV[1] = now (unix seconds)
# ARGV[2] = window/period (seconds)
# ARGV[3] = limit
# ARGV[4] = unique member for this request
# Returns 1 if allowed, 0 if the limit is exceeded.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local period = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, 0, now - period)
local count = redis.call('ZCARD', key)
if count >= limit then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, period + 2)
return 1
"""

_script = None


def _get_script():
    global _script
    if _script is None:
        _script = redis_client.register_script(_SLIDING_WINDOW_LUA)
    return _script


def check_rate_limit_key(
    key: str,
    limit: int = 5,
    period: int = 60,
    *,
    fail_open: bool = True,
) -> bool:
    """Return True if the request is allowed under the limit.

    The check is atomic (single Lua round-trip), so it holds under
    concurrent bursts. ``fail_open`` controls behavior when Redis is
    unreachable: reads may fail open (allow), but sensitive endpoints
    (login/register/verify/reset) MUST pass ``fail_open=False`` so an
    outage cannot silently disable their limits.
    """
    now = int(time.time())
    member = f"{now}:{uuid.uuid4().hex}"
    try:
        allowed = _get_script()(keys=[key], args=[now, period, limit, member])
        return bool(allowed)
    except redis.RedisError as exc:
        logger.warning(
            "Rate-limit backend unavailable for key %s (fail_open=%s): %s",
            key,
            fail_open,
            exc,
        )
        return fail_open


def check_rate_limit(
    user_id: int,
    limit: int = 5,
    period: int = 60,
    *,
    fail_open: bool = True,
) -> bool:
    return check_rate_limit_key(
        f"rl:{user_id}", limit=limit, period=period, fail_open=fail_open
    )
