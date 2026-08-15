"""Crudle façade — SQLAlchemy backend (one-shot + transaction)."""

import tempfile

from sqlalchemy import Column, Integer, String

from src.crudle import Crudle, SQLAlchemy


def _crud():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    backend = SQLAlchemy(f"sqlite:///{tmp.name}")
    crud = Crudle(backend)
    return crud


class TestCrudleSQLAlchemy:
    def test_model_is_base_plus_mixin(self):
        crud = _crud()

        class User(crud.Model):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        crud.create_all()

        assert issubclass(User, crud.backend.Base)
        user = crud.insert(User, name="Ada")
        assert user.id is not None
        assert user.name == "Ada"
        assert crud.get(User, user.id).name == "Ada"
        assert crud.get_by(User, name="Ada").id == user.id
        assert crud.count(User) == 1
        assert len(crud.list(User)) == 1

    def test_update_and_delete(self):
        crud = _crud()

        class User(crud.Model):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        crud.create_all()
        user = crud.insert(User, name="Ada")

        updated = crud.update(User, user.id, name="Grace")
        assert updated.name == "Grace"
        assert crud.get(User, user.id).name == "Grace"

        crud.delete(User, user.id)
        assert crud.get(User, user.id) is None

    def test_transaction_commits_once(self):
        crud = _crud()

        class User(crud.Model):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        crud.create_all()

        def body(db):
            a = db.insert(User, name="Ada")
            b = db.insert(User, name="Grace")
            return a.id, b.id

        id_a, id_b = crud.transaction(body)
        assert crud.count(User) == 2
        assert crud.get(User, id_a).name == "Ada"
        assert crud.get(User, id_b).name == "Grace"

    def test_transaction_rolls_back_on_error(self):
        crud = _crud()

        class User(crud.Model):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        crud.create_all()

        def body(db):
            db.insert(User, name="Ada")
            raise RuntimeError("boom")

        try:
            crud.transaction(body)
        except RuntimeError:
            pass

        assert crud.count(User) == 0

    def test_session_escape_hatch(self):
        crud = _crud()

        class User(crud.Model):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        crud.create_all()

        def body(db):
            db.insert(User, name="Ada")
            return db.count(User)

        assert crud.transaction(body) == 1

    def test_engine_escape_hatch(self):
        crud = _crud()
        assert crud.backend.engine is not None
        assert crud.backend.session_factory is not None
