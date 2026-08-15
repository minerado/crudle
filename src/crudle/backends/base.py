"""Backend protocol for Crudle façades."""

from typing import Any, Callable, Protocol, TypeVar

T = TypeVar("T")


class Backend(Protocol):
    """Owns storage lifecycle and runs transactional work."""

    @property
    def Model(self) -> type: ...

    def create_all(self) -> None: ...

    def drop_all(self) -> None: ...

    def transaction(self, fn: Callable[[Any], T]) -> T: ...
