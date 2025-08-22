"""
Image downloader implementation following Single Responsibility Principle
"""

import requests
import urllib3
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..core.interfaces import IImageDownloader, ImageTask, DownloadResult
from ..storage.managers.sequential_manager import SequentialStorageManager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HTTPImageDownloader(IImageDownloader):
    """HTTP image downloader implementing IImageDownloader interface"""
    
    def __init__(self, storage_manager: SequentialStorageManager, content_filter, timeout: int = 15):
        self.storage_manager = storage_manager
        self.content_filter = content_filter
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Create session with connection pooling
        self.session = self._create_optimized_session()
    
    def _create_optimized_session(self) -> requests.Session:
        """Create an optimized session with connection pooling and retries"""
        session = requests.Session()
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=20,  # Connection pool size
            pool_maxsize=20,      # Max connections per host
            max_retries=Retry(
                total=3,           # Total retries
                backoff_factor=0.3, # Exponential backoff
                status_forcelist=[500, 502, 503, 504]  # Retry on server errors
            )
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    async def download_image(self, image_task: ImageTask) -> DownloadResult:
        """Download a single image"""
        try:
            # Quick URL-based filtering first
            if not self.content_filter.quick_url_filter(image_task.image_url):
                return DownloadResult(
                    success=False,
                    file_path=None,
                    error_message="URL filtered out",
                    image_hash=None,
                    width=None,
                    height=None
                )
            
            # Download image content using connection pooling
            response = self.session.get(
                image_task.image_url, 
                headers=self.headers, 
                timeout=self.timeout, 
                verify=False
            )
            
            if response.status_code != 200:
                return DownloadResult(
                    success=False,
                    file_path=None,
                    error_message=f"HTTP {response.status_code}",
                    image_hash=None,
                    width=None,
                    height=None
                )
            
            content = response.content
            
            # Basic validation
            if not self.storage_manager.validate_image(content):
                return DownloadResult(
                    success=False,
                    file_path=None,
                    error_message="Image validation failed",
                    image_hash=None,
                    width=None,
                    height=None
                )
            
            # Content validation (human detection, content type)
            is_human, content_type = self._validate_content(content)
            
            # Get image format and dimensions
            width, height = self.storage_manager.get_image_dimensions(content)
            if not width or not height:
                return DownloadResult(
                    success=False,
                    file_path=None,
                    error_message="Could not determine image dimensions",
                    image_hash=None,
                    width=None,
                    height=None
                )
            
            # Determine format from URL or content
            format = self._get_image_format(image_task.image_url, content)
            
            # Get next filename
            filename, filepath = self.storage_manager.get_next_filename(image_task.image_url, format)
            
            # Save image
            if not self.storage_manager.save_image(content, filepath):
                return DownloadResult(
                    success=False,
                    file_path=None,
                    error_message="Failed to save image",
                    image_hash=None,
                    width=None,
                    height=None
                )
            
            # Calculate hash
            image_hash = self.storage_manager.calculate_image_hash(content)
            
            return DownloadResult(
                success=True,
                file_path=filepath,
                error_message=None,
                image_hash=image_hash,
                width=width,
                height=height,
                is_human=is_human,
                content_type=content_type
            )
            
        except Exception as e:
            return DownloadResult(
                success=False,
                file_path=None,
                error_message=str(e),
                image_hash=None,
                width=None,
                height=None
            )
    
    def _validate_content(self, image_content: bytes) -> tuple[bool, str]:
        """Validate image content for human detection and content type"""
        try:
            # Import content validator
            from ..core.content_validator import ContentValidator
            validator = ContentValidator()
            return validator.validate_image_content(image_content)
        except Exception as e:
            # If validation fails, assume it's not human and content type is unknown
            return False, "unknown"
    
    def _get_image_format(self, url: str, content: bytes) -> str:
        """Determine image format from URL or content"""
        # Try to get format from URL
        url_lower = url.lower()
        if '.jpg' in url_lower or '.jpeg' in url_lower:
            return 'jpg'
        elif '.png' in url_lower:
            return 'png'
        elif '.webp' in url_lower:
            return 'webp'
        elif '.gif' in url_lower:
            return 'gif'
        
        # Try to determine from content
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(content))
            format = img.format.lower()
            if format in ['jpeg', 'jpg']:
                return 'jpg'
            elif format in ['png', 'webp', 'gif']:
                return format
        except:
            pass
        
        # Default to jpg
        return 'jpg'
    
    def download_with_retry(self, image_task: ImageTask, max_retries: int = 2) -> DownloadResult:
        """Download image with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                # For synchronous retry, we need to handle this differently
                # Since this is a synchronous method, we'll just call the async one once
                import asyncio
                result = asyncio.run(self.download_image(image_task))
                if result.success:
                    return result
                
                if attempt < max_retries:
                    print(f"    ⚠️  Download failed on attempt {attempt + 1}, retrying...")
                    import time
                    time.sleep(1)  # Brief delay before retry
                    
            except Exception as e:
                if attempt < max_retries:
                    print(f"    ⚠️  Error on attempt {attempt + 1}: {e}, retrying...")
                    import time
                    time.sleep(2)  # Longer delay for errors
                else:
                    print(f"    ❌ Failed after {max_retries + 1} attempts: {e}")
        
        return DownloadResult(
            success=False,
            file_path=None,
            error_message="Max retries exceeded",
            image_hash=None,
            width=None,
            height=None
        )
    
    def get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"
    
    def is_valid_image_url(self, url: str) -> bool:
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
