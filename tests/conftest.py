import os
import tempfile

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from tests.utils.db import create_database, drop_database, migrate_head  # noqa: E402

# Create a temporary SQLite database file
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
temp_db.close()

# Use SQLite for testing (default)
TEST_URL = f"sqlite:///{temp_db.name}"

# Opt-in Postgres for FTS / q operator and DISTINCT ON stress tests
POSTGRES_URL = os.environ.get("CRUDLE_TEST_DATABASE_URL")

# Create the base class for models
Base = declarative_base()


def get_db():
    # This will be overridden in tests
    pass


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "postgres: requires Postgres (FTS / DISTINCT ON); set CRUDLE_TEST_DATABASE_URL to run",
    )


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.postgres tests unless CRUDLE_TEST_DATABASE_URL is set."""
    if POSTGRES_URL:
        return
    skip_postgres = pytest.mark.skip(
        reason="CRUDLE_TEST_DATABASE_URL not set; Postgres-only tests skipped"
    )
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip_postgres)


def _ensure_unaccent_simple(connection) -> None:
    """Bootstrap the text search config hardcoded by SQLAlchemyQueryField."""
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    connection.execute(
        text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_ts_config WHERE cfgname = 'unaccent_simple'
              ) THEN
                CREATE TEXT SEARCH CONFIGURATION unaccent_simple (COPY = simple);
                ALTER TEXT SEARCH CONFIGURATION unaccent_simple
                  ALTER MAPPING FOR hword, hword_part, word
                  WITH unaccent, simple;
              END IF;
            END
            $$;
            """
        )
    )


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


# ---- Opt-in Postgres engine for FTS / q operator tests ----
@pytest.fixture(scope="session")
def postgres_engine():
    if not POSTGRES_URL:
        yield None
        return

    eng = create_engine(POSTGRES_URL, pool_pre_ping=True)
    with eng.begin() as conn:
        _ensure_unaccent_simple(conn)
        Base.metadata.create_all(conn)

    try:
        yield eng
    finally:
        with eng.begin() as conn:
            Base.metadata.drop_all(conn)
        eng.dispose()


@pytest.fixture()
def postgres_db(postgres_engine):
    """Session fixture for @pytest.mark.postgres tests (FTS)."""
    if postgres_engine is None:
        pytest.skip(
            "CRUDLE_TEST_DATABASE_URL not set; Postgres FTS tests skipped"
        )

    connection = postgres_engine.connect()
    outer = connection.begin()

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
        outer.rollback()
        connection.close()
