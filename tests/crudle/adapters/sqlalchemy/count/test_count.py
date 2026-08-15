"""Count overview — SQLAlchemy adapter.

Basics, ignored list options, and light combos. Deeper coverage:

- ``test_count_ops.py`` — filter operators
- ``test_count_q.py`` — text search (``__q`` / ``search``, Postgres)
- ``test_count_assoc.py`` — relationship filters
- ``test_count_distinct_on.py`` — ``distinct_on`` cardinality
- ``test_count_custom.py`` — ``Queries`` filters
"""

from tests.models import Item, ItemList, Tag


# ---------------------------------------------------------------------------
# Basics
# ---------------------------------------------------------------------------


class TestCountBasics:
    def test_total(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)
        Item.insert(db, name="c", color="green", price=30)

        assert Item.count(db) == 3

    def test_empty_table(self, db):
        assert Item.count(db) == 0

    def test_empty_filters_kwarg(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="blue", price=20)

        assert Item.count(db, **{}) == 2

    def test_different_models(self, db):
        Item.insert(db, name="a", color="red")
        ItemList.insert(db, name="L1")
        ItemList.insert(db, name="L2")
        Tag.insert(db, name="t1")

        assert Item.count(db) == 1
        assert ItemList.count(db) == 2
        assert Tag.count(db) == 1


# ---------------------------------------------------------------------------
# Ignored list options
# ---------------------------------------------------------------------------


class TestCountIgnoresListOptions:
    def test_limit_skip(self, db):
        Item.insert(db, name="a", color="red")
        Item.insert(db, name="b", color="blue")
        Item.insert(db, name="c", color="green")

        assert Item.count(db, limit=1) == 3
        assert Item.count(db, skip=2) == 3
        assert Item.count(db, limit=1, skip=1) == 3

    def test_sort(self, db):
        Item.insert(db, name="a", color="red", price=30)
        Item.insert(db, name="b", color="blue", price=10)

        assert Item.count(db, sort=[{"field": "price", "order": "asc"}]) == 2

    def test_select_return_dict(self, db):
        Item.insert(db, name="a", color="red", price=10)
        Item.insert(db, name="b", color="red", price=20)
        Item.insert(db, name="c", color="blue", price=30)

        assert Item.count(db, select=["name"]) == 3
        assert Item.count(db, return_dict=True) == 3
