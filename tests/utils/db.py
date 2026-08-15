from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from alembic.config import Config
from alembic import command
import os


def create_database(url: str):
    """Create SQLite database by creating the tables directly."""
    # For SQLite, we don't need to create a separate database
    # Just ensure the directory exists
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Create tables using the models (import registers metadata)
    from tests.conftest import Base, TEST_URL
    import tests.models  # noqa: F401
    import tests.models_delete_cascade  # noqa: F401

    engine = create_engine(TEST_URL)
    Base.metadata.create_all(engine)
    engine.dispose()


def drop_database(url: str):
    """Drop SQLite database by removing the file."""
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            os.remove(db_path)


def migrate_head(url: str):
    """For SQLite, we create tables directly instead of using Alembic."""
    # Since we're using SQLite for testing, we'll create tables directly
    # This is simpler than setting up Alembic migrations for tests
    pass
