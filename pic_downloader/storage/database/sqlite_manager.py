"""
Database manager implementation following Single Responsibility Principle
"""

import sqlite3
from typing import List, Set, Tuple, Optional
from pathlib import Path
from ...core.interfaces import IDatabaseManager

class SQLiteDatabaseManager(IDatabaseManager):
    """SQLite database manager implementing IDatabaseManager interface"""
    
    def __init__(self, db_path: str = "image_sources.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        """Get database connection with foreign key enforcement enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _init_db(self):
        """Initialize database with proper schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create tables with proper foreign key constraints
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_urls INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                domain TEXT,
                visited BOOLEAN DEFAULT FALSE,
                images_found INTEGER DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (search_id) REFERENCES searches (id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloaded_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url_id INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                image_hash TEXT UNIQUE,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                width INTEGER,
                height INTEGER,
                is_human BOOLEAN DEFAULT NULL,
                content_type TEXT DEFAULT NULL,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_url_id) REFERENCES source_urls (id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes for foreign key columns to improve performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_urls_search_id ON source_urls (search_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloaded_images_source_url_id ON downloaded_images (source_url_id)')
        
        # Create additional useful indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_urls_visited ON source_urls (visited)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_urls_domain ON source_urls (domain)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloaded_images_hash ON downloaded_images (image_hash)')
        
        conn.commit()
        conn.close()
    
    def create_search(self, query: str) -> int:
        """Create new search entry"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO searches (query) VALUES (?)', (query,))
        search_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return search_id
    
    def store_urls(self, search_id: int, urls: Set[str]) -> int:
        """Store URLs for a search"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        new_count = 0
        for url in urls:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            cursor.execute('''
                INSERT OR IGNORE INTO source_urls (search_id, url, domain)
                VALUES (?, ?, ?)
            ''', (search_id, url, domain))
            if cursor.rowcount > 0:
                new_count += 1
        
        # Update search total
        cursor.execute('UPDATE searches SET total_urls = ? WHERE id = ?', 
                      (len(urls), search_id))
        
        conn.commit()
        conn.close()
        return new_count
    
    def get_unvisited_urls(self, search_id: int, limit: int = 25) -> List[Tuple[int, str]]:
        """Get unvisited URLs"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, url FROM source_urls 
            WHERE search_id = ? AND visited = FALSE 
            ORDER BY id LIMIT ?
        ''', (search_id, limit))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def mark_visited(self, url_id: int, images_found: int, error_msg: str = None):
        """Mark URL as visited"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE source_urls 
            SET visited = TRUE, images_found = ?, error_message = ?
            WHERE id = ?
        ''', (images_found, error_msg, url_id))
        conn.commit()
        conn.close()
    
    def store_downloaded_image(self, source_url_id: int, image_url: str, image_hash: str, 
                              file_path: str, file_size: int, width: int, height: int,
                              is_human: bool = None, content_type: str = None) -> bool:
        """Store downloaded image metadata"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO downloaded_images 
                (source_url_id, image_url, image_hash, file_path, file_size, width, height, is_human, content_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (source_url_id, image_url, image_hash, file_path, file_size, width, height, is_human, content_type))
            
            # For INSERT OR IGNORE, we need to check if the insert actually happened
            # by checking if the image_hash exists after the insert
            if image_hash:
                cursor.execute('SELECT id FROM downloaded_images WHERE image_hash = ?', (image_hash,))
                exists = cursor.fetchone()
                success = exists is not None
            else:
                # If no hash, assume success (this shouldn't happen in normal operation)
                success = True
            
            if success:
                conn.commit()
            
            conn.close()
            return success
            
        except Exception as e:
            print(f"Database error in store_downloaded_image: {e}")  # Debug logging
            conn.close()
            return False
    
    def is_duplicate_image(self, image_hash: str) -> bool:
        """Check if image hash already exists"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT file_path FROM downloaded_images WHERE image_hash = ?', (image_hash,))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def get_existing_hashes(self) -> Set[str]:
        """Get all existing image hashes"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT image_hash FROM downloaded_images WHERE image_hash IS NOT NULL')
        hashes = cursor.fetchall()
        conn.close()
        return {h[0] for h in hashes}
