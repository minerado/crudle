"""Count ``distinct_on`` — SQLAlchemy adapter.

Matches list cardinality. Field-list ``DISTINCT ON`` requires Postgres.
"""

import pytest

from tests.models import Item


def test_empty_list_is_noop(db):
    Item.insert(db, name="a", color="red", price=10)
    Item.insert(db, name="b", color="blue", price=20)

    assert Item.count(db, distinct_on=[]) == 2


@pytest.mark.postgres
def test_one_per_key(postgres_db):
    Item.insert(postgres_db, name="a", color="red", price=10)
    Item.insert(postgres_db, name="b", color="red", price=20)
    Item.insert(postgres_db, name="c", color="blue", price=30)

    assert Item.count(postgres_db, distinct_on=["color"]) == 2
    assert len(Item.list(postgres_db, distinct_on=["color"], limit=None)) == 2


@pytest.mark.postgres
def test_matches_list_cardinality(postgres_db):
    Item.insert(postgres_db, name="a", color="red", price=10)
    Item.insert(postgres_db, name="b", color="red", price=20)
    Item.insert(postgres_db, name="c", color="blue", price=30)
    Item.insert(postgres_db, name="d", color="green", price=40)

    listed = Item.list(
        postgres_db,
        distinct_on=["color"],
        sort=[{"field": "price", "order": "desc"}],
        limit=None,
    )
    assert Item.count(postgres_db, distinct_on=["color"]) == len(listed)


@pytest.mark.postgres
def test_with_filter(postgres_db):
    Item.insert(postgres_db, name="a", color="red", price=10)
    Item.insert(postgres_db, name="b", color="red", price=20)
    Item.insert(postgres_db, name="c", color="blue", price=30)

    assert Item.count(postgres_db, color="red", distinct_on=["color"]) == 1


@pytest.mark.postgres
def test_with_ne_none(postgres_db):
    Item.insert(postgres_db, name="a", color="red", price=10)
    Item.insert(postgres_db, name="b", color="red", price=None)
    Item.insert(postgres_db, name="c", color="blue", price=30)

    assert Item.count(postgres_db, distinct_on=["color"], price__ne=None) == 2
