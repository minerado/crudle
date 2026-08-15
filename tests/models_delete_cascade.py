"""Cascade policy fixtures for delete tests (Ecto on_delete vocabulary).

Kept separate from ``tests.models`` so list/count/get suites stay on the
default ``:nothing`` Item graph.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.crudle import SQLAlchemyAdapter
from tests.conftest import Base


class ParentNothing(Base, SQLAlchemyAdapter):
    """Ecto ``on_delete: :nothing`` — no ORM cascade, no FK ondelete."""

    __tablename__ = "cascade_parents_nothing"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    children = relationship("ChildNothing", back_populates="parent")


class ChildNothing(Base, SQLAlchemyAdapter):
    __tablename__ = "cascade_children_nothing"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    parent_id = Column(Integer, ForeignKey("cascade_parents_nothing.id"))

    parent = relationship("ParentNothing", back_populates="children")


class ParentDeleteAll(Base, SQLAlchemyAdapter):
    """Ecto ``on_delete: :delete_all`` — ORM cascade + FK CASCADE."""

    __tablename__ = "cascade_parents_delete_all"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    children = relationship(
        "ChildDeleteAll",
        back_populates="parent",
        cascade="all, delete",
    )


class ChildDeleteAll(Base, SQLAlchemyAdapter):
    __tablename__ = "cascade_children_delete_all"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    parent_id = Column(
        Integer,
        ForeignKey("cascade_parents_delete_all.id", ondelete="CASCADE"),
    )

    parent = relationship("ParentDeleteAll", back_populates="children")


class ParentNilify(Base, SQLAlchemyAdapter):
    """Ecto ``on_delete: :nilify_all`` — nullable FK + SET NULL."""

    __tablename__ = "cascade_parents_nilify"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    children = relationship("ChildNilify", back_populates="parent")


class ChildNilify(Base, SQLAlchemyAdapter):
    __tablename__ = "cascade_children_nilify"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    parent_id = Column(
        Integer,
        ForeignKey("cascade_parents_nilify.id", ondelete="SET NULL"),
        nullable=True,
    )

    parent = relationship("ParentNilify", back_populates="children")


class ParentRestrict(Base, SQLAlchemyAdapter):
    """Ecto ``on_delete: :restrict`` — FK RESTRICT when children exist."""

    __tablename__ = "cascade_parents_restrict"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    children = relationship("ChildRestrict", back_populates="parent")


class ChildRestrict(Base, SQLAlchemyAdapter):
    __tablename__ = "cascade_children_restrict"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    parent_id = Column(
        Integer,
        ForeignKey("cascade_parents_restrict.id", ondelete="RESTRICT"),
        nullable=False,
    )

    parent = relationship("ParentRestrict", back_populates="children")
