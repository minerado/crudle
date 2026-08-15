"""Crudle façade — Memory backend."""

from pydantic import BaseModel, Field

from src.crudle import Crudle, Memory


class TestCrudleMemory:
    def test_oneshot_and_transaction(self):
        crud = Crudle(Memory())

        class Item(BaseModel):
            id: int | None = None
            name: str = Field(..., min_length=1)

        item = crud.insert(Item, name="Widget")
        assert item.id is not None
        assert crud.get(Item, item.id).name == "Widget"
        assert crud.count(Item) == 1

        def body(db):
            a = db.insert(Item, name="A")
            b = db.insert(Item, name="B")
            return a.id, b.id

        crud.transaction(body)
        assert crud.count(Item) == 3

    def test_transaction_rolls_back_on_error(self):
        crud = Crudle(Memory())

        class Item(BaseModel):
            id: int | None = None
            name: str = Field(..., min_length=1)

        crud.insert(Item, name="keep")

        def body(db):
            db.insert(Item, name="gone")
            raise RuntimeError("boom")

        try:
            crud.transaction(body)
        except RuntimeError:
            pass

        assert crud.count(Item) == 1
        assert crud.get_by(Item, name="keep") is not None
        assert crud.get_by(Item, name="gone") is None
