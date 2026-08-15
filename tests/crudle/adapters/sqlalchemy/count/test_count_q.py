"""Count text-search (`q`) — SQLAlchemy / Postgres FTS.

Twin concern to ``list/test_list_q.py`` applied to ``count``. Opt in with:

    CRUDLE_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres \\
      pytest -m postgres

Without the env var, these tests are skipped.
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


class TestCountQ:
    def test_field_q(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        assert Item.count(postgres_db, name__q="Apple") == 1

    def test_prefix_match(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        assert Item.count(postgres_db, name__q="Appl") == 1

    def test_anded_with_filter(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Apple MacBook", color="blue", price=20)

        assert Item.count(postgres_db, name__q="Apple", color="red") == 1

    def test_miss_is_zero(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        assert Item.count(postgres_db, name__q="Nokia") == 0

    def test_bare_search_over_search_fields(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)
        Item.insert(postgres_db, name="Samsung Galaxy", color="blue", price=20)

        with search_fields("name"):
            assert Item.count(postgres_db, search="Apple") == 1

    def test_bare_q_alias(self, postgres_db):
        Item.insert(postgres_db, name="Apple iPhone", color="red", price=10)

        with search_fields("name"):
            assert Item.count(postgres_db, q="Apple") == 1
