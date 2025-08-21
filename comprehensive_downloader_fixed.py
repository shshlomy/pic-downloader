#!/usr/bin/env python3
"""
Fixed Multi-threaded Image Downloader with proper duplicate detection
Fixes:
1. Hash calculation after PIL processing (not before)
2. Better image relevance filtering
3. Improved Wikipedia content filtering
"""

import asyncio
import hashlib
import html as html_lib
import os
import re
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Set, List, Tuple, Optional

import aiohttp
import requests
import urllib3
from PIL import Image
from playwright.async_api import async_playwright, Page

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FixedURLDatabase:
    """Enhanced database with proper hash handling"""
    
    def __init__(self, db_path: str = "image_sources.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
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
                search_id INTEGER,
                url TEXT NOT NULL,
                domain TEXT,
                visited BOOLEAN DEFAULT FALSE,
                images_found INTEGER DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (search_id) REFERENCES searches (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloaded_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url_id INTEGER,
                image_url TEXT NOT NULL,
                image_hash TEXT UNIQUE,  -- Hash of the FINAL saved file
                file_path TEXT NOT NULL,
                file_size INTEGER,
                width INTEGER,
                height INTEGER,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_url_id) REFERENCES source_urls (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def image_exists_by_final_hash(self, file_hash: str) -> Tuple[bool, Optional[str]]:
        """Check if image exists by final file hash"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT file_path FROM downloaded_images WHERE image_hash = ?', (file_hash,))
        result = cursor.fetchone()
        conn.close()
        return (True, result[0]) if result else (False, None)
    
    def save_image_info(self, source_url_id: int, image_url: str, file_hash: str, 
                       file_path: str, file_size: int, width: int, height: int) -> bool:
        """Save image info with final file hash"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO downloaded_images 
                (source_url_id, image_url, image_hash, file_path, file_size, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (source_url_id, image_url, file_hash, file_path, file_size, width, height))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success
        except sqlite3.IntegrityError:
            return False
    
    def create_search(self, query: str) -> int:
        """Create new search entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO searches (query) VALUES (?)', (query,))
        search_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return search_id
    
    def store_urls(self, search_id: int, urls: Set[str]) -> int:
        """Store URLs for a search"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_count = 0
        for url in urls:
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
    
    def get_unvisited_urls(self, search_id: int, limit: int = 50) -> List[Tuple[int, str]]:
        """Get unvisited URLs"""
        conn = sqlite3.connect(self.db_path)
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE source_urls 
            SET visited = TRUE, images_found = ?, error_message = ?
            WHERE id = ?
        ''', (images_found, error_msg, url_id))
        conn.commit()
        conn.close()

class ImprovedImageFilter:
    """Enhanced image filtering to avoid irrelevant images"""
    
    # Skip domains that typically don't have relevant person images
    SKIP_DOMAINS = {
        'google.', 'facebook.', 'twitter.', 'instagram.', 'linkedin.', 'youtube.',
        'reddit.', 'pinterest.', 'tiktok.', 'snapchat.', 'auth.fandom.',
        'static.wikia.', 'www.w3.org', 'www.wapforum.org', 'ads.', 'analytics.',
        'tracking.', 'pixel.', 'beacon.', 'metrics.'
    }
    
    # Common irrelevant image patterns
    IRRELEVANT_PATTERNS = [
        r'logo', r'icon', r'favicon', r'sprite', r'button', r'arrow', r'nav',
        r'menu', r'header', r'footer', r'sidebar', r'banner', r'ad[_-]',
        r'placeholder', r'loading', r'spinner', r'blank', r'default',
        r'wikipedia.*logo', r'wikimedia.*logo', r'commons.*logo'
    ]
    
    def is_valid_source_url(self, url: str) -> bool:
        """Enhanced URL validation"""
        if not url or len(url) < 10:
            return False
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            # Skip problematic domains
            for skip_domain in self.SKIP_DOMAINS:
                if skip_domain in domain:
                    return False
            
            # Limit complex fandom subdomains
            if 'fandom.com' in domain and domain.count('.') > 2:
                return False
            
            return True
            
        except:
            return False
    
    def is_relevant_image_url(self, img_url: str, context_url: str = "") -> bool:
        """Check if image URL is likely relevant"""
        try:
            img_url_lower = img_url.lower()
            
            # Check for irrelevant patterns
            for pattern in self.IRRELEVANT_PATTERNS:
                if re.search(pattern, img_url_lower):
                    return False
            
            # Skip very small dimension indicators
            if re.search(r'(\d+)x(\d+)', img_url_lower):
                match = re.search(r'(\d+)x(\d+)', img_url_lower)
                if match:
                    width, height = int(match.group(1)), int(match.group(2))
                    if width < 150 or height < 150:
                        return False
            
            # Skip thumbnail indicators
            if any(thumb in img_url_lower for thumb in ['thumb', 'thumbnail', 'small', 'mini']):
                # But allow if it's a reasonably sized thumbnail
                if not re.search(r'(250|300|400|500)px', img_url_lower):
                    return False
            
            return True
            
        except:
            return True  # If in doubt, include it

class FixedMultiThreadedDownloader:
    """Fixed downloader with proper duplicate detection"""
    
    def __init__(self, query: str, max_images: int = 30, max_workers: int = 5):
        self.query = query
        self.max_images = max_images
        self.max_workers = max_workers
        
        # Create download directory
        sanitized_query = re.sub(r'[^\w\s-]', '', query).strip()
        sanitized_query = re.sub(r'[-\s]+', ' ', sanitized_query)
        self.download_dir = Path("downloads") / sanitized_query
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.db = FixedURLDatabase()
        self.filter = ImprovedImageFilter()
        
        # Thread-safe tracking
        self.lock = threading.Lock()
        self.downloaded_hashes = set()
        self.new_downloads = 0
        self.skipped_duplicates = 0
        
        # Load existing hashes
        self._load_existing_hashes()
    
    def _load_existing_hashes(self):
        """Load existing image hashes from database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT image_hash FROM downloaded_images WHERE image_hash IS NOT NULL')
        hashes = cursor.fetchall()
        conn.close()
        
        self.downloaded_hashes = {h[0] for h in hashes}
        print(f"📊 Loaded {len(self.downloaded_hashes)} existing image hashes from database")
    
    def download_image_sync_fixed(self, img_url: str, source_url_id: int) -> bool:
        """Fixed synchronous image download with proper hash calculation"""
        try:
            # Skip irrelevant images
            if not self.filter.is_relevant_image_url(img_url):
                return False
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(img_url, headers=headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                return False
            
            content = response.content
            
            # Validate image first
            try:
                img = Image.open(BytesIO(content))
                width, height = img.size
                
                # Skip very small images
                if width < 150 or height < 150:
                    return False
                
                # Skip tiny file sizes
                if len(content) < 8000:  # 8KB minimum
                    return False
                
            except Exception:
                return False
            
            # Check max images limit
            with self.lock:
                if self.new_downloads >= self.max_images:
                    return False
            
            # Save image to get the final file content
            domain = urlparse(img_url).netloc.replace('.', '_')
            
            with self.lock:
                existing_files = list(self.download_dir.glob("*.jpg")) + \
                               list(self.download_dir.glob("*.jpeg")) + \
                               list(self.download_dir.glob("*.png")) + \
                               list(self.download_dir.glob("*.webp"))
                next_num = len(existing_files)
                
                filename = f"{next_num:03d}_{domain}.{img.format.lower() if img.format else 'jpg'}"
                filepath = self.download_dir / filename
            
            # Save the image
            img.save(filepath, quality=95)
            
            # NOW calculate hash of the saved file (this is the fix!)
            with open(filepath, 'rb') as f:
                saved_content = f.read()
            file_hash = hashlib.md5(saved_content).hexdigest()
            
            # Check for duplicates using the correct hash
            with self.lock:
                # Check database
                exists, existing_path = self.db.image_exists_by_final_hash(file_hash)
                if exists:
                    self.skipped_duplicates += 1
                    print(f"    ⏭️  Skipped duplicate (exists as: {existing_path})")
                    # Remove the file we just saved
                    filepath.unlink()
                    return False
                
                # Check in-memory set
                if file_hash in self.downloaded_hashes:
                    self.skipped_duplicates += 1
                    print(f"    ⏭️  Skipped duplicate (already downloaded this session)")
                    filepath.unlink()
                    return False
            
            # Save to database with correct hash
            with self.lock:
                success = self.db.save_image_info(
                    source_url_id, img_url, file_hash, str(filepath),
                    len(saved_content), width, height
                )
                
                if success:
                    self.downloaded_hashes.add(file_hash)
                    self.new_downloads += 1
                    print(f"    ✅ Downloaded: {filename} ({width}x{height})")
                    return True
                else:
                    # Hash collision in database
                    self.skipped_duplicates += 1
                    print(f"    ⏭️  Skipped duplicate (hash collision in DB)")
                    filepath.unlink()
                    return False
                    
        except Exception as e:
            return False
    
    async def extract_google_urls(self) -> Set[str]:
        """Extract URLs from Google Images search"""
        urls = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Search Google Images
                search_url = f"https://www.google.com/search?q={self.query}&tbm=isch&hl=en"
                await page.goto(search_url, timeout=30000)
                
                # Accept consent if present
                await self._accept_consent(page)
                
                # Wait and scroll
                await page.wait_for_timeout(2000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                
                # Extract URLs from HTML
                html_content = await page.content()
                urls.update(await self._extract_urls_from_html(html_content))
                
            except Exception as e:
                print(f"⚠️ Error during extraction: {e}")
            finally:
                await browser.close()
        
        return urls
    
    async def _accept_consent(self, page: Page):
        """Accept Google consent form if present"""
        try:
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                '#L2AGLb',
                'button[aria-label*="Accept"]'
            ]
            for selector in consent_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        await elem.click()
                        await page.wait_for_timeout(500)
                        break
                except:
                    continue
        except:
            pass
    
    async def _extract_urls_from_html(self, html: str) -> Set[str]:
        """Extract URLs from HTML content"""
        urls = set()
        
        # Unescape HTML
        html = html_lib.unescape(html)
        
        # Extract imgrefurl parameters
        patterns = [
            r'imgrefurl=([^&"\']+)',
            r'"ru":"([^"]+)"',
            r'https?://[^\s"\'<>&]+(?:\.jpg|\.jpeg|\.png|\.gif|\.webp)'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, html):
                url = unquote(match.group(1) if 'imgrefurl' in pattern or 'ru' in pattern else match.group(0))
                url = url.replace('&amp;', '&')
                # Clean Google tracking parameters
                url = re.sub(r'&(sa|ved|usg)=[^&]*', '', url)
                
                if self.filter.is_valid_source_url(url):
                    urls.add(url)
        
        return urls
    
    async def visit_and_download_async(self, url_id: int, url: str) -> Tuple[int, List[str]]:
        """Visit website and extract image URLs"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    await page.goto(url, timeout=15000, wait_until='networkidle')
                    await page.wait_for_timeout(1000)
                    
                    # Scroll to load lazy images
                    await page.evaluate("""
                        window.scrollTo(0, document.body.scrollHeight);
                        setTimeout(() => window.scrollTo(0, 0), 500);
                    """)
                    await page.wait_for_timeout(1000)
                    
                    # Find image elements with improved selectors
                    image_selectors = [
                        'img[src*=".jpg"], img[src*=".jpeg"], img[src*=".png"], img[src*=".webp"]',
                        'img[data-src*=".jpg"], img[data-src*=".jpeg"], img[data-src*=".png"], img[data-src*=".webp"]',
                        'img[data-lazy-src*=".jpg"], img[data-lazy-src*=".jpeg"], img[data-lazy-src*=".png"], img[data-lazy-src*=".webp"]'
                    ]
                    
                    image_urls = []
                    
                    for selector in image_selectors:
                        elements = await page.query_selector_all(selector)
                        for elem in elements:
                            for attr in ['src', 'data-src', 'data-lazy-src']:
                                img_url = await elem.get_attribute(attr)
                                if img_url and img_url.startswith('http') and self.filter.is_relevant_image_url(img_url, url):
                                    image_urls.append(img_url)
                    
                    print(f"  Found {len(image_urls)} images")
                    
                except Exception as e:
                    await browser.close()
                    raise e
                
                await browser.close()
                return url_id, image_urls
                
        except Exception as e:
            return url_id, []
    
    async def run(self):
        """Run the fixed downloader"""
        print(f"\n{'='*60}")
        print(f"🚀 FIXED MULTI-THREADED IMAGE DOWNLOADER")
        print(f"{'='*60}")
        print(f"🔧 Configuration:")
        print(f"  • Max Workers: {self.max_workers}")
        print(f"  • Max Images: {self.max_images}")
        print(f"  • Duplicate Detection: Fixed (hash after save)")
        print(f"  • Image Filtering: Enhanced")
        
        # Create search
        search_id = self.db.create_search(self.query)
        print(f"\n📝 Created search #{search_id} for: {self.query}")
        
        # Extract URLs
        print(f"\n🔍 Searching Google Images for: {self.query}")
        urls = await self.extract_google_urls()
        
        if not urls:
            print("❌ No URLs found!")
            return
        
        print(f"✨ Found {len(urls)} unique source websites")
        
        # Store URLs
        new_count = self.db.store_urls(search_id, urls)
        print(f"💾 Stored {new_count} new URLs in database")
        
        if new_count == 0:
            print("ℹ️  All URLs already exist, checking for unvisited ones...")
        
        # Get unvisited URLs
        unvisited = self.db.get_unvisited_urls(search_id, limit=50)
        
        if not unvisited:
            print("✅ No unvisited URLs to process")
            return
        
        print(f"\n🎯 Visiting websites to collect image URLs...")
        
        # Visit websites and collect images
        all_image_tasks = []
        
        for url_id, url in unvisited[:25]:  # Process 25 at a time
            if self.new_downloads >= self.max_images:
                break
            
            print(f"\n🌐 Visiting: {urlparse(url).netloc}")
            try:
                url_id, image_urls = await self.visit_and_download_async(url_id, url)
                
                if image_urls:
                    print(f"  Found {len(image_urls)} images on page")
                    for img_url in image_urls[:10]:  # Limit per site
                        all_image_tasks.append((img_url, url_id))
                else:
                    self.db.mark_visited(url_id, 0, "No images found")
                    
            except Exception as e:
                print(f"  Error: {str(e)[:50]}...")
                self.db.mark_visited(url_id, 0, str(e))
        
        # Download images
        if all_image_tasks:
            print(f"\n⚡ Downloading {len(all_image_tasks)} images using {self.max_workers} threads...")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for img_url, url_id in all_image_tasks:
                    if self.new_downloads >= self.max_images:
                        break
                    
                    future = executor.submit(self.download_image_sync_fixed, img_url, url_id)
                    futures.append((future, url_id))
                
                url_image_counts = {}
                
                for future, url_id in futures:
                    try:
                        success = future.result(timeout=20)
                        if success:
                            url_image_counts[url_id] = url_image_counts.get(url_id, 0) + 1
                    except:
                        continue
                
                # Mark URLs as visited
                for url_id, count in url_image_counts.items():
                    self.db.mark_visited(url_id, count)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"📊 DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"  Search Query: {self.query}")
        print(f"  URLs Found: {len(urls)}")
        print(f"  URLs Visited: {len(unvisited)}")
        print(f"  New Images Downloaded: {self.new_downloads}")
        print(f"  Duplicates Skipped: {self.skipped_duplicates}")
        print(f"  Total Unique Images in DB: {len(self.downloaded_hashes)}")
        print(f"  Save Location: {self.download_dir}")
        print(f"  Database: {self.db.db_path}")
        print(f"{'='*60}")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 comprehensive_downloader_fixed.py \"search query\" [max_images] [max_workers]")
        sys.exit(1)
    
    query = sys.argv[1]
    max_images = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    downloader = FixedMultiThreadedDownloader(query, max_images, max_workers)
    await downloader.run()

if __name__ == "__main__":
    asyncio.run(main())
