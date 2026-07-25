"""Sadaqah domain permissions."""

from app.core.permissions import Permission, register_permission


# Permission registry - add domain-specific permissions here
register_permission(
    Permission(
        key="sadaqah.completions.read",
        description="View own activity completions",
    )
)

register_permission(
    Permission(
        key="sadaqah.completions.create",
        description="Create activity completions",
    )
)

register_permission(
    Permission(
        key="sadaqah.sessions.read",
        description="View own activity sessions",
    )
)

register_permission(
    Permission(
        key="sadaqah.sessions.create",
        description="Create activity sessions",
    )
)

register_permission(
    Permission(
        key="sadaqah.streaks.read",
        description="View own activity streaks",
    )
)

register_permission(
    Permission(
        key="sadaqah.analytics.read",
        description="View own activity analytics",
    )
)
