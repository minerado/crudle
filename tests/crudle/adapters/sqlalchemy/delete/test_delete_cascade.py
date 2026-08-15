"""Declared delete cascade — SQLAlchemy (Ecto on_delete vocabulary).

Policy lives on relationship / FK, not on ``delete`` / ``delete_by``.
SQLite needs ``PRAGMA foreign_keys=ON`` for SET NULL / RESTRICT (nilify /
restrict suites only). ``:nothing`` matches the default Item graph: no ORM
cascade and SQLite without FK enforcement, so children remain.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.models_delete_cascade import (
    ChildDeleteAll,
    ChildNilify,
    ChildNothing,
    ChildRestrict,
    ParentDeleteAll,
    ParentNilify,
    ParentNothing,
    ParentRestrict,
)


@pytest.fixture
def fk_on(db):
    """Enable SQLite FK enforcement for SET NULL / RESTRICT."""
    db.execute(text("PRAGMA foreign_keys=ON"))
    yield


class TestDeleteCascadeNothing:
    def test_parent_delete_leaves_children(self, db):
        parent = ParentNothing.insert(db, name="p")
        a = ChildNothing.insert(db, name="a", parent=parent)
        b = ChildNothing.insert(db, name="b", parent=parent)
        parent_id, a_id, b_id = parent.id, a.id, b.id

        parent.delete(db)

        assert ParentNothing.get(db, parent_id) is None
        assert ChildNothing.get(db, a_id) is not None
        assert ChildNothing.get(db, b_id) is not None


class TestDeleteCascadeDeleteAll:
    def test_parent_delete_removes_children(self, db):
        parent = ParentDeleteAll.insert(db, name="p")
        a = ChildDeleteAll.insert(db, name="a", parent=parent)
        b = ChildDeleteAll.insert(db, name="b", parent=parent)
        parent_id, a_id, b_id = parent.id, a.id, b.id

        parent.delete(db)

        assert ParentDeleteAll.get(db, parent_id) is None
        assert ChildDeleteAll.get(db, a_id) is None
        assert ChildDeleteAll.get(db, b_id) is None


class TestDeleteCascadeNilify:
    def test_parent_delete_nulls_child_fk(self, db, fk_on):
        parent = ParentNilify.insert(db, name="p")
        child = ChildNilify.insert(db, name="c", parent=parent)
        parent_id, child_id = parent.id, child.id

        parent.delete(db)

        assert ParentNilify.get(db, parent_id) is None
        remaining = ChildNilify.get(db, child_id)
        assert remaining is not None
        assert remaining.parent_id is None


class TestDeleteCascadeRestrict:
    def test_parent_delete_fails_when_children_exist(self, db, fk_on):
        parent = ParentRestrict.insert(db, name="p")
        ChildRestrict.insert(db, name="c", parent=parent)

        # FK RESTRICT: commit fails. Outer test txn is aborted after this;
        # the raise is the contract (same as Ecto/DB).
        with pytest.raises(IntegrityError):
            parent.delete(db)

    def test_parent_delete_ok_without_children(self, db, fk_on):
        parent = ParentRestrict.insert(db, name="p")
        parent_id = parent.id

        parent.delete(db)

        assert ParentRestrict.get(db, parent_id) is None
