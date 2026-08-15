"""Memory backend — wraps MemoryAdapter for the Crudle façade."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from pydantic import BaseModel

from ..adapters.memory import MemoryAdapter

T = TypeVar("T")


class _MemoryHandle:
    """CRUD surface over MemoryAdapter (already session-less)."""

    def __init__(self, adapter: MemoryAdapter):
        self.session = adapter  # escape hatch: the store itself
        self._adapter = adapter

    def insert(self, model: type, **kwargs: Any) -> Any:
        return self._adapter.insert(model, **kwargs)

    def get(self, model: type, id: Any) -> Any:
        return self._adapter.get(model, id)

    def get_by(self, model: type, **filters: Any) -> Any:
        return self._adapter.get_by(model, **filters)

    def list(self, model: type, **filters: Any) -> list:
        return self._adapter.list(model, **filters)

    def count(self, model: type, **filters: Any) -> int:
        return self._adapter.count(model, **filters)

    def update(self, model: type, id: Any, **kwargs: Any) -> Any:
        return self._adapter.update(model, id, **kwargs)

    def update_by(
        self,
        model: type,
        filters: dict,
        should_raise: bool = False,
        **kwargs: Any,
    ) -> Any:
        return self._adapter.update_by(
            model, filters, should_raise=should_raise, **kwargs
        )

    def upsert_by(self, model: type, filters: dict, **kwargs: Any) -> Any:
        return self._adapter.upsert_by(model, filters, **kwargs)

    def delete(self, model: type, id: Any) -> Any:
        return self._adapter.delete(model, id)

    def delete_by(self, model: type, **filters: Any) -> Any:
        return self._adapter.delete_by(model, **filters)


class Memory:
    """Backend: in-memory store + optional Pydantic ``Model`` base."""

    def __init__(self, adapter: MemoryAdapter | None = None):
        self._adapter = adapter if adapter is not None else MemoryAdapter()
        self.Model = BaseModel
        self.adapter = self._adapter

    def create_all(self) -> None:
        return None

    def drop_all(self) -> None:
        self._adapter.clear_data()

    def transaction(self, fn: Callable[[_MemoryHandle], T]) -> T:
        handle = _MemoryHandle(self._adapter)
        snapshot = self._adapter._snapshot_store()
        try:
            return fn(handle)
        except Exception:
            self._adapter._restore_store(snapshot)
            raise
