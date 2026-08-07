"""Event bus abstraction for Mizan.

Every domain publishes events. Other domains consume them.
No direct service-to-service coupling.

Example events:
- FamilyCreated
- ReflectionCreated
- GoalCompleted
- NotificationGenerated
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable


@dataclass
class DomainEvent:
    event_type: str
    domain: str
    payload: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    idempotency_key: str | None = None


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """In-process event bus with async handlers.

    Handlers are awaited sequentially. A failing handler does not prevent
    other handlers from running — errors are logged and swallowed so the
    publisher never blocks on a broken subscriber.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Deliver an event to all subscribers.

        Each handler is awaited independently; exceptions are logged and
        swallowed so one broken subscriber cannot block the rest.
        """
        import logging

        logger = logging.getLogger(__name__)
        for handler in self._handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s",
                    getattr(handler, "__name__", handler),
                    event.event_type,
                )

    def has_subscribers(self, event_type: str) -> bool:
        return bool(self._handlers.get(event_type))


event_bus = EventBus()
