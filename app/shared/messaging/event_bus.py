from abc import ABC, abstractmethod
from collections.abc import Callable


class EventBus(ABC):
    @abstractmethod
    def subscribe[E](self, event_type: type[E], handler: Callable[[E], None]) -> None:
        pass

    @abstractmethod
    def publish(self, event: object) -> None:
        pass
