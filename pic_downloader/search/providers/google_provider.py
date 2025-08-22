"""
Google search provider implementation following Single Responsibility Principle
"""

import re
import html as html_lib
from typing import Set
from urllib.parse import urlparse, unquote, quote_plus
from playwright.async_api import async_playwright, Page
from ...core.interfaces import ISearchProvider, SearchResult

class GoogleSearchProvider(ISearchProvider):
    """Google search provider implementing ISearchProvider interface"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
    
    async def search(self, query: str) -> SearchResult:
        """Perform a Google Images search and return results"""
        urls = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                # Search Google Images with proper encoding
                encoded_query = quote_plus(query)
                search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch&hl=en"
                await page.goto(search_url, timeout=self.timeout)
                
                # Accept consent if present
                await self._accept_consent(page)
                
                # Wait and scroll for more results
                await page.wait_for_timeout(2000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)
                
                # Extract URLs from HTML
                html_content = await page.content()
                urls.update(await self._extract_urls_from_html(html_content))
                
            except Exception as e:
                print(f"⚠️ Error during Google search for '{query}': {e}")
            finally:
                await browser.close()
        
        return SearchResult(
            query=query,
            urls=urls,
            search_date=self._get_current_timestamp()
        )
    
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
            pass  # Ignore consent errors
    
    async def _extract_urls_from_html(self, html: str) -> Set[str]:
        """Extract URLs from HTML content"""
        urls = set()
        
        # Unescape HTML
        html = html_lib.unescape(html)
        
        # Find image URLs in various formats
        patterns = [
            r'https://[^"\s]+\.(?:jpg|jpeg|png|webp|gif)',
            r'https://[^"\s]+/images/[^"\s]+',
            r'https://[^"\s]+/wp-content/uploads/[^"\s]+',
            r'https://[^"\s]+/content/[^"\s]+',
            r'https://[^"\s]+/assets/[^"\s]+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # Clean up URL
                url = match.split('"')[0].split("'")[0].split('\\')[0]
                if self._is_valid_image_url(url):
                    urls.add(url)
        
        return urls
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL"""
        try:
            parsed = urlparse(url)
            
            # Must have valid scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Must have valid image extension
            path_lower = parsed.path.lower()
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            if not any(path_lower.endswith(ext) for ext in valid_extensions):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async def search_with_scrolling(self, query: str, scroll_count: int = 3) -> SearchResult:
        """Perform search with multiple scrolls for more results"""
        urls = set()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                # Initial search
                encoded_query = quote_plus(query)
                search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch&hl=en"
                await page.goto(search_url, timeout=self.timeout)
                
                # Accept consent
                await self._accept_consent(page)
                
                # Multiple scrolls for more results
                for i in range(scroll_count):
                    await page.wait_for_timeout(1000)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                    
                    # Extract URLs after each scroll
                    html_content = await page.content()
                    new_urls = await self._extract_urls_from_html(html_content)
                    urls.update(new_urls)
                    
                    print(f"   📊 Scroll {i+1}/{scroll_count}: Found {len(new_urls)} new URLs (Total: {len(urls)})")
                
            except Exception as e:
                print(f"⚠️ Error during scrolling search for '{query}': {e}")
            finally:
                await browser.close()
        
        return SearchResult(
            query=query,
            urls=urls,
            search_date=self._get_current_timestamp()
        )
