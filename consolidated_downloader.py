#!/usr/bin/env python3
"""
Consolidated Image Downloader - All searches for same subject go to one folder
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

# Import content-aware filtering
from content_aware_filter import content_filter

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ConsolidatedDownloader:
    """Downloader that consolidates all searches for same subject into one folder"""
    
    def __init__(self, query: str, max_images: int = 30, max_workers: int = 5):
        self.original_query = query
        self.max_images = max_images
        self.max_workers = max_workers
        
        # Extract base subject from query (first 1-2 words)
        self.base_subject = self._extract_base_subject(query)
        
        # Create consolidated download directory
        self.download_dir = Path("downloads") / self.base_subject
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self.db_path = "image_sources.db"
        self._init_db()
        
        # Thread-safe tracking
        self.lock = threading.Lock()
        self.downloaded_hashes = set()
        self.new_downloads = 0
        self.skipped_duplicates = 0
        
        # Load existing hashes
        self._load_existing_hashes()
    
    def _extract_base_subject(self, query: str) -> str:
        """Extract the main subject from search query"""
        # Clean the query
        query = query.lower().strip()
        
        # Remove common search modifiers
        modifiers = [
            'photos', 'pictures', 'images', 'pics',
            'fashion', 'style', 'outfit', 'dress', 'clothes',
            'concert', 'performance', 'stage', 'live',
            'red carpet', 'photoshoot', 'magazine', 'glamour',
            'beauty', 'portrait', 'singer', 'music',
            'eurovision', 'israel', 'unicorn'
        ]
        
        # Split into words
        words = query.split()
        
        # Remove modifiers and keep main subject
        filtered_words = []
        for word in words:
            if word not in modifiers:
                filtered_words.append(word)
        
        # Take first 2 words as base subject
        base_subject = ' '.join(filtered_words[:2]) if filtered_words else query
        
        # Sanitize for folder name
        base_subject = re.sub(r'[^\w\s-]', '', base_subject).strip()
        base_subject = re.sub(r'[-\s]+', ' ', base_subject)
        
        return base_subject
    
    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                image_hash TEXT UNIQUE,
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
    
    def _load_existing_hashes(self):
        """Load existing image hashes from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT image_hash FROM downloaded_images WHERE image_hash IS NOT NULL')
        hashes = cursor.fetchall()
        conn.close()
        
        self.downloaded_hashes = {h[0] for h in hashes}
        print(f"📊 Loaded {len(self.downloaded_hashes)} existing image hashes from database")
    
    def _get_next_filename(self, img_url: str) -> str:
        """Get next available filename in consolidated folder"""
        domain = urlparse(img_url).netloc.replace('.', '_')
        
        # Get existing files in the consolidated folder
        existing_files = list(self.download_dir.glob("*.jpg")) + \
                        list(self.download_dir.glob("*.jpeg")) + \
                        list(self.download_dir.glob("*.png")) + \
                        list(self.download_dir.glob("*.webp"))
        
        next_num = len(existing_files)
        return f"{next_num:03d}_{domain}"
    
    def download_image_sync(self, img_url: str, source_url_id: int) -> bool:
        """Download image with consolidated folder logic and content-aware filtering"""
        try:
            # Quick URL-based filtering first
            if not content_filter.quick_url_filter(img_url):
                print(f"    ⏭️  Skipped by quick URL filter: {img_url}")
                return False
            
            # Legacy URL filtering (keep for now)
            if not self._is_relevant_image_url(img_url):
                return False
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(img_url, headers=headers, timeout=15, verify=False)
            
            if response.status_code != 200:
                return False
            
            content = response.content
            
            # Basic validation first
            try:
                img = Image.open(BytesIO(content))
                width, height = img.size
                
                if width < 150 or height < 150 or len(content) < 8000:
                    return False
                
            except Exception:
                return False
            
            # CONTENT-AWARE FILTERING - The main enhancement!
            try:
                is_relevant, analysis = content_filter.is_relevant_image(
                    content, img_url, self.original_query, min_relevance_score=0.4
                )
                
                if not is_relevant:
                    print(f"    🚫 Content filter rejected (score: {analysis['relevance_score']:.2f}): {analysis['content_type']}")
                    if analysis.get('reasons'):
                        print(f"       Reasons: {'; '.join(analysis['reasons'][:2])}")  # Show first 2 reasons
                    return False
                else:
                    print(f"    ✨ Content filter approved (score: {analysis['relevance_score']:.2f}): {analysis['content_type']}")
                    if analysis.get('has_faces'):
                        print(f"       👤 Detected {analysis['face_count']} face(s) with confidence {analysis['face_confidence']:.2f}")
                        
            except Exception as e:
                # If content filtering fails, fall back to basic filtering
                print(f"    ⚠️  Content filtering failed, using basic filter: {e}")
                # Continue with download since basic validation passed
            
            # Check max images limit
            with self.lock:
                if self.new_downloads >= self.max_images:
                    return False
                
                # Get filename in consolidated folder
                filename_base = self._get_next_filename(img_url)
                filename = f"{filename_base}.{img.format.lower() if img.format else 'jpg'}"
                filepath = self.download_dir / filename
            
            # Save the image
            img.save(filepath, quality=95)
            
            # Calculate hash of saved file
            with open(filepath, 'rb') as f:
                saved_content = f.read()
            file_hash = hashlib.md5(saved_content).hexdigest()
            
            # Check for duplicates
            with self.lock:
                # Check database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT file_path FROM downloaded_images WHERE image_hash = ?', (file_hash,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    self.skipped_duplicates += 1
                    print(f"    ⏭️  Skipped duplicate (exists as: {result[0]})")
                    filepath.unlink()
                    return False
                
                # Check in-memory set
                if file_hash in self.downloaded_hashes:
                    self.skipped_duplicates += 1
                    print(f"    ⏭️  Skipped duplicate (already downloaded this session)")
                    filepath.unlink()
                    return False
            
            # Save to database
            with self.lock:
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR IGNORE INTO downloaded_images 
                        (source_url_id, image_url, image_hash, file_path, file_size, width, height)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (source_url_id, img_url, file_hash, str(filepath), len(saved_content), width, height))
                    
                    if cursor.rowcount > 0:
                        self.downloaded_hashes.add(file_hash)
                        self.new_downloads += 1
                        print(f"    ✅ Downloaded: {filename} ({width}x{height})")
                        conn.commit()
                        conn.close()
                        return True
                    else:
                        conn.close()
                        filepath.unlink()
                        self.skipped_duplicates += 1
                        return False
                        
                except sqlite3.IntegrityError:
                    conn.close()
                    filepath.unlink()
                    self.skipped_duplicates += 1
                    return False
                    
        except Exception as e:
            return False
    
    def _is_relevant_image_url(self, img_url: str) -> bool:
        """Check if image URL is relevant"""
        try:
            img_url_lower = img_url.lower()
            
            # Skip irrelevant patterns
            irrelevant_patterns = [
                r'logo', r'icon', r'favicon', r'sprite', r'button', r'arrow', r'nav',
                r'menu', r'header', r'footer', r'sidebar', r'banner', r'ad[_-]',
                r'placeholder', r'loading', r'spinner', r'blank', r'default'
            ]
            
            for pattern in irrelevant_patterns:
                if re.search(pattern, img_url_lower):
                    return False
            
            # Skip very small dimension indicators
            if re.search(r'(\d+)x(\d+)', img_url_lower):
                match = re.search(r'(\d+)x(\d+)', img_url_lower)
                if match:
                    width, height = int(match.group(1)), int(match.group(2))
                    if width < 150 or height < 150:
                        return False
            
            return True
            
        except:
            return True
    
    async def extract_google_urls(self) -> Set[str]:
        """Extract URLs from Google Images search"""
        urls = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Search Google Images
                search_url = f"https://www.google.com/search?q={self.original_query}&tbm=isch&hl=en"
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
                
                if self._is_valid_source_url(url):
                    urls.add(url)
        
        return urls
    
    def _is_valid_source_url(self, url: str) -> bool:
        """Check if URL is valid for visiting"""
        if not url or len(url) < 10:
            return False
        
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            skip_domains = {
                'google.', 'facebook.', 'twitter.', 'instagram.', 'linkedin.', 'youtube.',
                'reddit.', 'pinterest.', 'tiktok.', 'snapchat.', 'auth.fandom.',
                'static.wikia.', 'www.w3.org', 'www.wapforum.org'
            }
            
            for skip_domain in skip_domains:
                if skip_domain in domain:
                    return False
            
            return True
            
        except:
            return False
    
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
                    
                    # Find image elements
                    image_selectors = [
                        'img[src*=".jpg"], img[src*=".jpeg"], img[src*=".png"], img[src*=".webp"]',
                        'img[data-src*=".jpg"], img[data-src*=".jpeg"], img[data-src*=".png"], img[data-src*=".webp"]'
                    ]
                    
                    image_urls = []
                    
                    for selector in image_selectors:
                        elements = await page.query_selector_all(selector)
                        for elem in elements:
                            for attr in ['src', 'data-src']:
                                img_url = await elem.get_attribute(attr)
                                if img_url and img_url.startswith('http') and self._is_relevant_image_url(img_url):
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
        """Run the consolidated downloader"""
        print(f"\n{'='*60}")
        print(f"🚀 CONSOLIDATED IMAGE DOWNLOADER")
        print(f"{'='*60}")
        print(f"🔧 Configuration:")
        print(f"  • Search Query: '{self.original_query}'")
        print(f"  • Base Subject: '{self.base_subject}'")
        print(f"  • Consolidated Folder: {self.download_dir}")
        print(f"  • Max Workers: {self.max_workers}")
        print(f"  • Max Images: {self.max_images}")
        print(f"  • Duplicate Detection: Global (across all searches)")
        
        # Create search in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO searches (query) VALUES (?)', (self.original_query,))
        search_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"\n📝 Created search #{search_id} for: {self.original_query}")
        print(f"📁 All images will be saved to: {self.download_dir}")
        
        # Extract URLs
        print(f"\n🔍 Searching Google Images...")
        urls = await self.extract_google_urls()
        
        if not urls:
            print("❌ No URLs found!")
            return
        
        print(f"✨ Found {len(urls)} unique source websites")
        
        # Store URLs
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
        
        cursor.execute('UPDATE searches SET total_urls = ? WHERE id = ?', 
                      (len(urls), search_id))
        conn.commit()
        conn.close()
        
        print(f"💾 Stored {new_count} new URLs in database")
        
        # Get unvisited URLs
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, url FROM source_urls 
            WHERE search_id = ? AND visited = FALSE 
            ORDER BY id LIMIT 50
        ''', (search_id,))
        unvisited = cursor.fetchall()
        conn.close()
        
        if not unvisited:
            print("✅ No unvisited URLs to process")
            return
        
        print(f"\n🎯 Visiting websites to collect image URLs...")
        
        # Visit websites and collect images
        all_image_tasks = []
        
        for url_id, url in unvisited:
            if self.new_downloads >= self.max_images:
                break
            
            print(f"\n🌐 Visiting: {urlparse(url).netloc}")
            try:
                url_id, image_urls = await self.visit_and_download_async(url_id, url)
                
                if image_urls:
                    print(f"  Found {len(image_urls)} images on page")
                    for img_url in image_urls[:10]:
                        all_image_tasks.append((img_url, url_id))
                else:
                    # Mark as visited
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute('UPDATE source_urls SET visited = TRUE, images_found = 0 WHERE id = ?', (url_id,))
                    conn.commit()
                    conn.close()
                    
            except Exception as e:
                print(f"  Error: {str(e)[:50]}...")
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('UPDATE source_urls SET visited = TRUE, error_message = ? WHERE id = ?', (str(e), url_id))
                conn.commit()
                conn.close()
        
        # Download images
        if all_image_tasks:
            print(f"\n⚡ Downloading {len(all_image_tasks)} images using {self.max_workers} threads...")
            print(f"📁 All images will be saved to: {self.download_dir}")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for img_url, url_id in all_image_tasks:
                    if self.new_downloads >= self.max_images:
                        break
                    
                    future = executor.submit(self.download_image_sync, img_url, url_id)
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
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                for url_id, count in url_image_counts.items():
                    cursor.execute('UPDATE source_urls SET visited = TRUE, images_found = ? WHERE id = ?', (count, url_id))
                conn.commit()
                conn.close()
        
        # Print summary
        total_images_in_folder = len(list(self.download_dir.glob("*.jpg")) + 
                                     list(self.download_dir.glob("*.jpeg")) + 
                                     list(self.download_dir.glob("*.png")) + 
                                     list(self.download_dir.glob("*.webp")))
        
        print(f"\n{'='*60}")
        print(f"📊 DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"  Search Query: {self.original_query}")
        print(f"  Base Subject: {self.base_subject}")
        print(f"  URLs Found: {len(urls)}")
        print(f"  URLs Visited: {len(unvisited)}")
        print(f"  New Images Downloaded: {self.new_downloads}")
        print(f"  Duplicates Skipped: {self.skipped_duplicates}")
        print(f"  Total Images in Folder: {total_images_in_folder}")
        print(f"  Consolidated Location: {self.download_dir}")
        print(f"{'='*60}")

async def main():
    if len(sys.argv) < 2:
        print("🖼️  Consolidated Image Downloader")
        print("=" * 40)
        print("Usage: python3 consolidated_downloader.py \"search query\" [max_images] [max_workers]")
        print("\nExamples:")
        print("  python3 consolidated_downloader.py \"noa kirel\"")
        print("  python3 consolidated_downloader.py \"noa kirel fashion\" 50")
        print("  python3 consolidated_downloader.py \"michael jordan basketball\" 100 8")
        print("\nFeatures:")
        print("  • Consolidates all searches for same subject into ONE folder")
        print("  • Global duplicate detection across all searches")
        print("  • Enhanced image filtering")
        sys.exit(1)
    
    query = sys.argv[1]
    max_images = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    downloader = ConsolidatedDownloader(query, max_images, max_workers)
    await downloader.run()

if __name__ == "__main__":
    asyncio.run(main())
