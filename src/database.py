"""
Модуль работы с SQLite базой данных.
Отслеживает обработанные статьи для предотвращения дубликатов.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger("NewsBot.Database")


class Database:
    """
    SQLite база данных для хранения обработанных статей.
    
    Использует контекстный менеджер для безопасной работы с соединениями.
    Поддерживает WAL режим для лучшей производительности.
    """

    def __init__(self, db_path: str):
        """
        Инициализация базы данных.
        
        Args:
            db_path: путь к файлу базы данных
        """
        self.db_path = db_path
        self._init_schema()
        logger.info(f"База данных инициализирована: {db_path}")

    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения с БД."""
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
        """Инициализация схемы базы данных."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Включаем WAL режим для лучшей производительности
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Основная таблица обработанных статей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Индексы для быстрого поиска
                    CONSTRAINT unique_link UNIQUE (link)
                )
            """)
            
            # Индекс по ссылке для быстрой проверки дубликатов
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_link 
                ON processed_articles(link)
            """)
            
            # Индекс по дате для аналитики
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON processed_articles(processed_at)
            """)

    def is_processed(self, link: str) -> bool:
        """
        Проверка, была ли статья уже обработана.
        
        Args:
            link: URL статьи
            
        Returns:
            True если статья уже в базе
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
            logger.error(f"Ошибка проверки в БД: {e}")
            return False

    def mark_processed(self, link: str, title: str, source: str = "") -> bool:
        """
        Отметить статью как обработанную.
        
        Args:
            link: URL статьи
            title: заголовок статьи
            source: название источника
            
        Returns:
            True если запись успешно добавлена
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
            logger.error(f"Ошибка записи в БД: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику базы данных.
        
        Returns:
            Словарь со статистикой
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Общее количество
                cursor.execute("SELECT COUNT(*) FROM processed_articles")
                total = cursor.fetchone()[0]
                
                # Последняя обработка
                cursor.execute("""
                    SELECT processed_at FROM processed_articles 
                    ORDER BY processed_at DESC LIMIT 1
                """)
                row = cursor.fetchone()
                last_processed = row[0] if row else None
                
                # Статистика по источникам
                cursor.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM processed_articles 
                    GROUP BY source
                """)
                by_source = {row["source"]: row["count"] for row in cursor.fetchall()}
                
                # За последние 24 часа
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
            logger.error(f"Ошибка получения статистики: {e}")
            return {"total": 0, "last_processed": None, "by_source": {}, "last_24h": 0}

    def cleanup_old(self, days: int = 30) -> int:
        """
        Удаление старых записей для экономии места.
        
        Args:
            days: возраст записей в днях для удаления
            
        Returns:
            Количество удаленных записей
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
                    # Оптимизируем БД после удаления
                    cursor.execute("VACUUM")
                    logger.info(f"Удалено {deleted} старых записей")
                    
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка очистки БД: {e}")
            return 0
