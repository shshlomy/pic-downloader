"""
Web image extractor implementation following Single Responsibility Principle
"""

import re
from typing import List, Tuple
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from ..core.interfaces import IImageExtractor, IProgressTracker
import asyncio

class WebImageExtractor(IImageExtractor):
    """Web image extractor implementing IImageExtractor interface"""
    
    def __init__(self, progress_tracker: IProgressTracker, headless: bool = True, timeout: int = 30000):
        self.progress_tracker = progress_tracker
        self.headless = headless
        self.timeout = timeout
    
    async def extract_images(self, url: str, url_id: int) -> Tuple[int, List[str]]:
        """Extract image URLs from a website"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                
                # Set dynamic timeout based on domain performance
                timeout = self._get_dynamic_timeout(url)
                
                # Navigate to URL with optimized loading
                await page.goto(url, timeout=self.timeout, wait_until='domcontentloaded')
                
                # Wait for page to load (dynamic timeout)
                await page.wait_for_timeout(timeout)
                
                # Extract image URLs
                image_urls = await page.evaluate('''
                    () => {
                        const images = document.querySelectorAll('img');
                        const urls = [];
                        for (let img of images) {
                            if (img.src && img.src.startsWith('http')) {
                                urls.push(img.src);
                            }
                        }
                        return urls;
                    }
                ''')
                
                # Close browser
                await browser.close()
                
                # Filter and return unique URLs
                unique_urls = list(set(image_urls))
                return url_id, unique_urls  # Return url_id, not count
                
        except Exception as e:
            self.progress_tracker.log_activity(f"Error extracting images from {url}: {e}", "ERROR")
            return url_id, []  # Return url_id with empty list on error
    
    def _get_dynamic_timeout(self, url: str) -> int:
        """Get dynamic timeout based on domain performance"""
        try:
            domain = urlparse(url).netloc
            
            # Fast domains get shorter timeout
            fast_domains = {
                'media.gettyimages.com', 'upload.wikimedia.org', 'commons.wikimedia.org',
                'cdn-images.dzcdn.net', 'i.pinimg.com', 'live.staticflickr.com',
                'm.media-amazon.com', 'ssl.gstatic.com', 'pbs.twimg.com'
            }
            
            # Slow domains get longer timeout
            slow_domains = {
                'www.thierrylebraly.com', 'shop.maiermedia-gmbh.com', 'www.algemeiner.com',
                'thefashioninsider.com', 'www.kveller.com', 'israeled.org'
            }
            
            if domain in fast_domains:
                return 200  # 200ms for fast domains
            elif domain in slow_domains:
                return 800  # 800ms for slow domains
            else:
                return 300  # 300ms default (reduced from 500ms)
                
        except:
            return 300  # Default timeout
    
    def _extract_images_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract image URLs from HTML content"""
        image_urls = []
        
        # Unescape HTML
        # html = html_lib.unescape(html) # This line was removed as per the new_code
        
        # Find image URLs in various formats
        patterns = [
            r'https://[^"\s]+\.(?:jpg|jpeg|png|webp|gif)',
            r'https://[^"\s]+/images/[^"\s]+',
            r'https://[^"\s]+/wp-content/uploads/[^"\s]+',
            r'https://[^"\s]+/content/[^"\s]+',
            r'https://[^"\s]+/assets/[^"\s]+',
            r'https://[^"\s]+/uploads/[^"\s]+',
            r'https://[^"\s]+/media/[^"\s]+'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # Clean up URL
                url = match.split('"')[0].split("'")[0].split('\\')[0]
                if self._is_valid_image_url(url, base_url):
                    image_urls.append(url)
        
        return image_urls
    
    def _is_valid_image_url(self, url: str, base_url: str) -> bool:
        """Check if URL is a valid image URL"""
        try:
            # Handle relative URLs
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                parsed_base = urlparse(base_url)
                url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
            elif not url.startswith('http'):
                parsed_base = urlparse(base_url)
                url = f"{parsed_base.scheme}://{parsed_base.netloc}/{url}"
            
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
            
            # Filter out common non-image patterns
            exclude_patterns = [
                'logo', 'icon', 'banner', 'ad', 'sponsor', 'tracking',
                'analytics', 'pixel', 'beacon', 'favicon'
            ]
            
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in exclude_patterns):
                return False
            
            return True
            
        except Exception:
            return False
    
    async def extract_images_with_retry(self, url: str, url_id: int, max_retries: int = 2) -> Tuple[int, List[str]]:
        """Extract images with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                url_id, image_urls = await self.extract_images(url, url_id)
                if image_urls:
                    return url_id, image_urls
                
                if attempt < max_retries:
                    print(f"    ⚠️  No images found on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(1)  # Brief delay before retry
                    
            except Exception as e:
                if attempt < max_retries:
                    print(f"    ⚠️  Error on attempt {attempt + 1}: {e}, retrying...")
                    await asyncio.sleep(2)  # Longer delay for errors
                else:
                    print(f"    ❌ Failed after {max_retries + 1} attempts: {e}")
        
        return url_id, []
    
    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"
    
    def _is_likely_image_page(self, html: str) -> bool:
        """Check if the page is likely to contain images"""
        html_lower = html.lower()
        
        # Check for image-related content
        image_indicators = [
            'img src', 'image', 'photo', 'picture', 'gallery',
            'album', 'portfolio', 'media', 'visual'
        ]
        
        return any(indicator in html_lower for indicator in image_indicators)
