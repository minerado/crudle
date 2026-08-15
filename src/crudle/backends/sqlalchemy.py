"""SQLAlchemy backend — engine, session factory, and Model base."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from ..adapters.sqlalchemy import SQLAlchemyAdapter

T = TypeVar("T")


class _SQLAlchemySessionHandle:
    """CRUD surface over a live Session; never commits (outer txn does)."""

    def __init__(self, session: Session):
        self.session = session

    def _flush(self) -> None:
        self.session.flush()

    def insert(self, model: type, **kwargs: Any) -> Any:
        obj = model.insert(self.session, commit=False, **kwargs)
        self._flush()
        return obj

    def get(self, model: type, id: Any) -> Any:
        return model.get(self.session, id)

    def get_by(self, model: type, **filters: Any) -> Any:
        return model.get_by(self.session, **filters)

    def list(self, model: type, **filters: Any) -> list:
        return model.list(self.session, **filters)

    def count(self, model: type, **filters: Any) -> int:
        return model.count(self.session, **filters)

    def update(self, model: type, id: Any, **kwargs: Any) -> Any:
        instance = model.get(self.session, id)
        if instance is None:
            return None
        updated = instance.update(self.session, commit=False, **kwargs)
        self._flush()
        return updated

    def update_by(
        self,
        model: type,
        filters: dict,
        should_raise: bool = False,
        **kwargs: Any,
    ) -> Any:
        updated = model.update_by(
            self.session,
            filters,
            should_raise=should_raise,
            commit=False,
            **kwargs,
        )
        if updated is not None:
            self._flush()
        return updated

    def upsert_by(self, model: type, filters: dict, **kwargs: Any) -> Any:
        updated = model.update_by(self.session, filters, commit=False, **kwargs)
        if updated is not None:
            self._flush()
            return updated
        attrs = model._attrs_for_upsert_insert(filters, kwargs)
        obj = model.insert(self.session, commit=False, **attrs)
        self._flush()
        return obj

    def delete(self, model: type, id: Any) -> Any:
        instance = model.get(self.session, id)
        if instance is None:
            return None
        deleted = instance.delete(self.session, commit=False)
        self._flush()
        return deleted

    def delete_by(self, model: type, **filters: Any) -> Any:
        instance = model.get_by(self.session, **filters)
        if instance is None:
            return None
        deleted = instance.delete(self.session, commit=False)
        self._flush()
        return deleted


class SQLAlchemy:
    """Backend: URL → engine + sessionmaker + ``Model`` (Base + mixin)."""

    def __init__(
        self,
        url: str,
        *,
        base: type | None = None,
        engine_kwargs: dict | None = None,
        session_kwargs: dict | None = None,
    ):
        engine_kwargs = dict(engine_kwargs or {})
        session_kwargs = dict(session_kwargs or {})
        session_kwargs.setdefault("autoflush", False)
        session_kwargs.setdefault("autocommit", False)
        session_kwargs.setdefault("expire_on_commit", False)

        self.url = url
        self.engine = create_engine(url, **engine_kwargs)
        self.Base = base if base is not None else declarative_base()

        class Model(self.Base, SQLAlchemyAdapter):
            __abstract__ = True

        self.Model = Model
        self._session_factory = sessionmaker(bind=self.engine, **session_kwargs)

    @property
    def metadata(self):
        return self.Base.metadata

    @property
    def session_factory(self):
        return self._session_factory

    def create_all(self) -> None:
        self.Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        self.Base.metadata.drop_all(self.engine)

    def transaction(self, fn: Callable[[_SQLAlchemySessionHandle], T]) -> T:
        session = self._session_factory()
        handle = _SQLAlchemySessionHandle(session)
        try:
            result = fn(handle)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
