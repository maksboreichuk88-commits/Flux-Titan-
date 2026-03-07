import os
import sqlite3
import pytest
from flux_titan.storage.sqlite import Database

@pytest.fixture
def test_db(tmp_path):
    """Provides a temporary SQLite database for testing."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    yield db
    
    # Cleanup after test if needed
    if db_path.exists():
        try:
            os.remove(db_path)
        except PermissionError:
            pass # Windows file lock, ignore in tmp_path

def test_initial_db_is_empty(test_db):
    stats = test_db.get_stats()
    assert stats["total"] == 0
    assert not test_db.is_processed("https://example.com/article1")

def test_article_processing_and_deduplication(test_db):
    url = "https://example.com/article1"
    
    # Mark as processed
    success = test_db.mark_processed(link=url, title="Test Article", source="TestFeed")
    assert success is True
    
    # Verify it is now marked as processed
    assert test_db.is_processed(url) is True
    
    # Try marking it again (should ignore and not fail, but returns False for insertion)
    success2 = test_db.mark_processed(link=url, title="Test Article Duplicate", source="TestFeed")
    assert success2 is False
    
    # Stats should show only 1 item
    stats = test_db.get_stats()
    assert stats["total"] == 1
    assert stats["by_source"].get("TestFeed") == 1

def test_cleanup_old_records(test_db):
    url1 = "https://old.com"
    test_db.mark_processed(link=url1, title="Old", source="Feed")
    
    # Verify cleanup runs without errors
    deleted = test_db.cleanup_old(days=30)
    assert deleted == 0
    assert test_db.is_processed(url1)  # Stays untouched
