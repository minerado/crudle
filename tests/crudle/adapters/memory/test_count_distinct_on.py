"""Count ``distinct_on`` — Memory adapter.

Twin of SQLAlchemy ``count/test_count_distinct_on.py`` (always runs locally).
"""

from tests.crudle.adapters.memory.models import Item


def test_empty_list_is_noop(db):
    db.insert(Item, name="a", color="red", price=10)
    db.insert(Item, name="b", color="blue", price=20)

    assert db.count(Item, distinct_on=[]) == 2


def test_one_per_key(db):
    db.insert(Item, name="a", color="red", price=10)
    db.insert(Item, name="b", color="red", price=20)
    db.insert(Item, name="c", color="blue", price=30)

    assert db.count(Item, distinct_on=["color"]) == 2
    assert len(db.list(Item, distinct_on=["color"], limit=None)) == 2


def test_matches_list_cardinality(db):
    db.insert(Item, name="a", color="red", price=10)
    db.insert(Item, name="b", color="red", price=20)
    db.insert(Item, name="c", color="blue", price=30)
    db.insert(Item, name="d", color="green", price=40)

    listed = db.list(
        Item,
        distinct_on=["color"],
        sort=[{"field": "price", "order": "desc"}],
        limit=None,
    )
    assert db.count(Item, distinct_on=["color"]) == len(listed)


def test_with_filter(db):
    db.insert(Item, name="a", color="red", price=10)
    db.insert(Item, name="b", color="red", price=20)
    db.insert(Item, name="c", color="blue", price=30)

    assert db.count(Item, color="red", distinct_on=["color"]) == 1


def test_with_ne_none(db):
    db.insert(Item, name="a", color="red", price=10)
    db.insert(Item, name="b", color="red", price=None)
    db.insert(Item, name="c", color="blue", price=30)

    assert db.count(Item, distinct_on=["color"], price__ne=None) == 2
