"""
SQLite database module.
Tracks processed articles to prevent duplicates.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger("NewsBot.Database")


class Database:
    """
    SQLite database for storing processed articles.
    
    Uses context manager for safe connection handling.
    Supports WAL mode for better performance.
    """

    def __init__(self, db_path: str):
        """
        Database initialization.
        
        Args:
            db_path: path to the database file
        """
        self.db_path = db_path
        self._init_schema()
        logger.info(f"Database initialized: {db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for DB connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Database schema initialization."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable WAL mode for better performance
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Main table for processed articles
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Indexes for fast search
                    CONSTRAINT unique_link UNIQUE (link)
                )
            """)
            
            # Index by link for fast duplicate checking
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_link 
                ON processed_articles(link)
            """)
            
            # Index by date for analytics
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON processed_articles(processed_at)
            """)

    def is_processed(self, link: str) -> bool:
        """
        Check if the article has already been processed.
        
        Args:
            link: article URL
            
        Returns:
            True if article is already in the database
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM processed_articles WHERE link = ? LIMIT 1",
                    (link,)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"DB search error: {e}")
            return False

    def mark_processed(self, link: str, title: str, source: str = "") -> bool:
        """
        Mark the article as processed.
        
        Args:
            link: article URL
            title: article title
            source: source name
            
        Returns:
            True if the record was successfully added
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO processed_articles (link, title, source)
                    VALUES (?, ?, ?)
                    """,
                    (link, title, source)
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"DB write error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total count
                cursor.execute("SELECT COUNT(*) FROM processed_articles")
                total = cursor.fetchone()[0]
                
                # Last processed
                cursor.execute("""
                    SELECT processed_at FROM processed_articles 
                    ORDER BY processed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                last_processed = row[0] if row else None
                
                # Statistics by source
                cursor.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM processed_articles 
                    GROUP BY source
                """)
                by_source = {row["source"]: row["count"] for row in cursor.fetchall()}
                
                # Last 24 hours
                cursor.execute("""
                    SELECT COUNT(*) FROM processed_articles 
                    WHERE processed_at > datetime('now', '-1 day')
                """)
                last_24h = cursor.fetchone()[0]
                
                return {
                    "total": total,
                    "last_processed": last_processed,
                    "by_source": by_source,
                    "last_24h": last_24h
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {"total": 0, "last_processed": None, "by_source": {}, "last_24h": 0}

    def cleanup_old(self, days: int = 30) -> int:
        """
        Delete old records to save space.
        
        Args:
            days: age of records in days to delete
            
        Returns:
            Number of deleted records
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    DELETE FROM processed_articles 
                    WHERE processed_at < datetime('now', '-{days} days')
                    """
                )
                deleted = cursor.rowcount
                
                if deleted > 0:
                    # Optimize DB after deletion
                    cursor.execute("VACUUM")
                    logger.info(f"Deleted {deleted} old records")
                    
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"DB cleanup error: {e}")
            return 0
