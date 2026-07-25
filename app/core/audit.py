"""Audit logging abstraction for Mizan.

Provides a reusable interface for recording who did what, when, and where.
Domains should use this instead of implementing their own audit logging.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    actor_id: int | None
    action: str
    domain: str
    resource_id: str | None = None
    resource_type: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger:
    def log(self, event: AuditEvent) -> None:
        logger.info(
            "AUDIT: %s %s on %s:%s by %s",
            event.action,
            event.domain,
            event.resource_type,
            event.resource_id,
            event.actor_id,
            extra={
                "audit": True,
                "actor_id": event.actor_id,
                "action": event.action,
                "domain": event.domain,
                "resource_id": event.resource_id,
                "resource_type": event.resource_type,
                "ip_address": event.ip_address,
                "user_agent": event.user_agent,
                "timestamp": event.timestamp.isoformat(),
                **event.details,
            },
        )


audit_logger = AuditLogger()
