"""
Pytest configuration for memory adapter tests.
"""

import pytest
from src.crudle.adapters.memory.adapter import MemoryAdapter


@pytest.fixture
def adapter():
    """Create a fresh memory adapter for each test."""
    adapter = MemoryAdapter()
    yield adapter
    # Clean up after each test
    adapter.clear_data()


@pytest.fixture
def db(adapter):
    """Alias for adapter to match SQLAlchemy test naming."""
    return adapter
