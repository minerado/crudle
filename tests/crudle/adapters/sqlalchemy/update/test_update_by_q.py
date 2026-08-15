"""Update_by text-search (`q`) — SQLAlchemy / Postgres FTS.

Opt in with CRUDLE_TEST_DATABASE_URL and ``pytest -m postgres``.
"""

from contextlib import contextmanager

import pytest

from tests.models import Item

pytestmark = pytest.mark.postgres


@contextmanager
def search_fields(*fields: str):
    previous = getattr(Item.Queries, "search_fields", None)
    Item.Queries.search_fields = list(fields)
    try:
        yield
    finally:
        if previous is None:
            if hasattr(Item.Queries, "search_fields"):
                delattr(Item.Queries, "search_fields")
        else:
            Item.Queries.search_fields = previous


class TestUpdateByQ:
    def test_field_q(self, postgres_db):
        keep = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        assert (
            Item.update_by(
                postgres_db, {"name__q": "Apple"}, name="hit"
            ).id
            == keep.id
        )
        assert Item.get(postgres_db, keep.id).name == "hit"

    def test_anded_with_filter(self, postgres_db):
        keep = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Apple MacBook", color="blue", price=20)

        assert (
            Item.update_by(
                postgres_db, {"name__q": "Apple", "color": "red"}, name="hit"
            ).id
            == keep.id
        )

    def test_miss(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        assert Item.update_by(postgres_db, {"name__q": "Nokia"}, name="x") is None

    def test_bare_search(self, postgres_db):
        keep = Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        with search_fields("name"):
            assert (
                Item.update_by(
                    postgres_db, {"search": "Apple"}, name="hit"
                ).id
                == keep.id
            )
