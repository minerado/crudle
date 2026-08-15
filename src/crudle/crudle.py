"""Crudle — thin Repo-style façade over a backend."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


class Crudle:
    """App entrypoint: ``Crudle(SQLAlchemy(...))`` / ``Crudle(Memory())``.

    One-shot CRUD opens a private transaction, commits, and returns data.
    Multi-step work uses ``transaction(fn)``; ``fn`` receives a handle with
    the same CRUD methods plus ``.session`` for raw escape.
    """

    def __init__(self, backend: Any):
        self.backend = backend

    @property
    def Model(self) -> type:
        return self.backend.Model

    def create_all(self) -> None:
        self.backend.create_all()

    def drop_all(self) -> None:
        self.backend.drop_all()

    def transaction(self, fn: Callable[[Any], T]) -> T:
        return self.backend.transaction(fn)

    def insert(self, model: type, **kwargs: Any) -> Any:
        return self.transaction(lambda db: db.insert(model, **kwargs))

    def get(self, model: type, id: Any) -> Any:
        return self.transaction(lambda db: db.get(model, id))

    def get_by(self, model: type, **filters: Any) -> Any:
        return self.transaction(lambda db: db.get_by(model, **filters))

    def list(self, model: type, **filters: Any) -> list:
        return self.transaction(lambda db: db.list(model, **filters))

    def count(self, model: type, **filters: Any) -> int:
        return self.transaction(lambda db: db.count(model, **filters))

    def update(self, model: type, id: Any, **kwargs: Any) -> Any:
        return self.transaction(lambda db: db.update(model, id, **kwargs))

    def update_by(
        self,
        model: type,
        filters: dict,
        should_raise: bool = False,
        **kwargs: Any,
    ) -> Any:
        return self.transaction(
            lambda db: db.update_by(
                model, filters, should_raise=should_raise, **kwargs
            )
        )

    def upsert_by(self, model: type, filters: dict, **kwargs: Any) -> Any:
        return self.transaction(lambda db: db.upsert_by(model, filters, **kwargs))

    def delete(self, model: type, id: Any) -> Any:
        return self.transaction(lambda db: db.delete(model, id))

    def delete_by(self, model: type, **filters: Any) -> Any:
        return self.transaction(lambda db: db.delete_by(model, **filters))
