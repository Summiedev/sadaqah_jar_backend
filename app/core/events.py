"""Event bus abstraction for Mizan.

Every domain publishes events. Other domains consume them.
No direct service-to-service coupling.

Example events:
- FamilyCreated
- ReflectionCreated
- GoalCompleted
- NotificationGenerated
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable


@dataclass
class DomainEvent:
    event_type: str
    domain: str
    payload: dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            await handler(event)


event_bus = EventBus()
