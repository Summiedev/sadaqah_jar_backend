"""Rapid-fire event deduplication.

This is a *separate* layer from the DB-level ``idempotency_key`` check in
``create_notification``. The DB check prevents duplicate rows once a
notification reaches persistence. This Redis layer suppresses genuinely
rapid duplicate *events* (e.g. a goal-update handler firing twice in the
same second) before they are ever enqueued, so we don't pay the cost of a
queue round-trip and a DB lookup for an event we already accepted moments
ago.

Implementation: ``SET key value NX EX ttl`` (atomic set-if-not-exists with
expiry). The first caller within the window claims the key and proceeds;
subsequent callers are told the event is a duplicate.

Fail-open policy: if Redis is unreachable we return ``True`` (claim
granted) so that a Redis outage never silently drops notifications. The
downstream DB idempotency key still protects against true duplicates.
"""

import logging

import redis

from app.core.cache import redis_client

logger = logging.getLogger(__name__)

# Default suppression window for rapid-fire duplicates. Long enough to
# absorb double-clicks / duplicate event publishes, short enough that a
# legitimately repeated event later on is not blocked.
DEFAULT_DEDUP_TTL_SECONDS = 60

_KEY_PREFIX = "notif:dedup:"


def claim_event(idempotency_key: str, ttl: int = DEFAULT_DEDUP_TTL_SECONDS) -> bool:
    """Attempt to claim an event key for processing.

    Returns ``True`` if this caller is the first to see ``idempotency_key``
    within the TTL window (i.e. it should proceed), and ``False`` if the
    event was already claimed (i.e. it is a rapid-fire duplicate and should
    be suppressed).

    Fails open: on any Redis error, returns ``True``.
    """
    if not idempotency_key:
        # No key means we cannot dedup; allow it through.
        return True
    redis_key = f"{_KEY_PREFIX}{idempotency_key}"
    try:
        # nx=True -> only set if absent; returns True when set, None otherwise.
        claimed = redis_client.set(redis_key, "1", nx=True, ex=ttl)
        return bool(claimed)
    except redis.RedisError as exc:
        logger.warning(
            "Dedup claim failed for %s, failing open: %s", idempotency_key, exc
        )
        return True


def release_event(idempotency_key: str) -> None:
    """Release a previously claimed event key.

    Useful when an enqueue fails and the caller wants a later retry of the
    *same* event to be allowed before the TTL expires. Best-effort only.
    """
    if not idempotency_key:
        return
    redis_key = f"{_KEY_PREFIX}{idempotency_key}"
    try:
        redis_client.delete(redis_key)
    except redis.RedisError as exc:
        logger.warning("Dedup release failed for %s: %s", idempotency_key, exc)
