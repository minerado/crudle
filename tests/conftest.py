import pytest
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from tests.utils.db import create_database, drop_database, migrate_head  # noqa: E402


# Create a temporary SQLite database file
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
temp_db.close()

# Use SQLite for testing
TEST_URL = f"sqlite:///{temp_db.name}"

# Create the base class for models
Base = declarative_base()


def get_db():
    # This will be overridden in tests
    pass


# ---- Create a fresh test DB for this run; migrate; drop at the end ----
@pytest.fixture(scope="session", autouse=True)
def _session_db_lifecycle():
    create_database(TEST_URL)
    migrate_head(TEST_URL)

    yield TEST_URL

    drop_database(TEST_URL)


# ---- Engine bound to the test DB for the session ----
@pytest.fixture(scope="session")
def engine(_session_db_lifecycle):
    eng = create_engine(_session_db_lifecycle, pool_pre_ping=True)
    try:
        yield eng
    finally:
        eng.dispose()


# ---- Per-test transaction + SAVEPOINT (route .commit() stays inside) ----
@pytest.fixture()
def db(engine):
    connection = engine.connect()
    outer = connection.begin()  # outer txn for the whole test

    SessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        outer.rollback()  # wipes all writes from this test
        connection.close()
