"""Base types for the reminder content library."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReminderEntry:
    """A single reminder content entry."""

    title: str
    message: str
    category: str
    source: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
