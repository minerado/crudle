"""Insert validation — Memory adapter (Pydantic).

SA insert does not run Pydantic; this suite is Memory-only.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from tests.crudle.adapters.memory.models import Item, Tag


class TestInsertValidation:
    def test_required_field(self, db):
        with pytest.raises(ValueError, match="Field required|validation error"):
            db.insert(Tag)

        tag = db.insert(Tag, name="valid_tag")
        assert tag.name == "valid_tag"

    def test_field_type(self, db):
        with pytest.raises(ValueError, match="validation error"):
            db.insert(Item, price="not_a_number")

        item = db.insert(Item, price=100)
        assert item.price == 100

    def test_string_too_long(self, db):
        with pytest.raises(ValueError, match="validation error"):
            db.insert(Item, name="x" * 200)

    def test_duplicate_id_raises(self, db):
        first = db.insert(Item, name="a", color="red")

        with pytest.raises(IntegrityError, match="Duplicate primary key"):
            db.insert(Item, id=first.id, name="b", color="blue")

        assert db.count(Item) == 1
        assert db.get(Item, first.id).name == "a"
