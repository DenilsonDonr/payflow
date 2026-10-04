import uuid
from abc import ABC, abstractmethod


class DomainEvent(ABC):
    """A fact the domain wants to announce, shaped so the outbox can store it uniformly."""

    # Stable identity of this notification (not of the aggregate it describes).
    # Declared as an attribute, not an abstract property, so frozen dataclass
    # events can supply it as a plain field.
    event_id: uuid.UUID

    @property
    @abstractmethod
    def aggregate_type(self) -> str: ...

    @property
    @abstractmethod
    def aggregate_id(self) -> uuid.UUID: ...

    @property
    @abstractmethod
    def event_type(self) -> str: ...

    @abstractmethod
    def payload(self) -> dict[str, object]:
        """JSON-safe representation of the event data."""
