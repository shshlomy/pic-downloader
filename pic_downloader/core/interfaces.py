"""
Core interfaces for the image downloader system following SOLID principles
"""

from abc import ABC, abstractmethod
from typing import List, Set, Tuple, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SearchResult:
    """Data class for search results"""
    query: str
    urls: Set[str]
    search_date: str

@dataclass
class ImageTask:
    """Data class for image download tasks"""
    image_url: str
    source_url_id: int
    priority: int = 1

@dataclass
class DownloadResult:
    """Data class for download results"""
    success: bool
    file_path: Optional[Path]
    error_message: Optional[str]
    image_hash: Optional[str]
    width: Optional[int]
    height: Optional[int]
    is_human: Optional[bool] = None
    content_type: Optional[str] = None

class ISearchProvider(ABC):
    """Interface for search providers (Google, Bing, etc.)"""
    
    @abstractmethod
    async def search(self, query: str) -> SearchResult:
        """Perform a search and return results"""
        pass

class IImageExtractor(ABC):
    """Interface for extracting images from websites"""
    
    @abstractmethod
    async def extract_images(self, url: str, url_id: int) -> Tuple[int, List[str]]:
        """Extract image URLs from a website"""
        pass

class IImageDownloader(ABC):
    """Interface for downloading images"""
    
    @abstractmethod
    async def download_image(self, image_task: ImageTask) -> DownloadResult:
        """Download a single image"""
        pass

class IContentFilter(ABC):
    """Interface for content filtering"""
    
    @abstractmethod
    def is_relevant_image(self, image_content: bytes, image_url: str, query: str, min_score: float = 0.4) -> Tuple[bool, Dict[str, Any]]:
        """Check if an image is relevant to the query"""
        pass

class IStorageManager(ABC):
    """Interface for storage operations"""
    
    @abstractmethod
    def get_next_filename(self, image_url: str, format: str) -> Tuple[str, Path]:
        """Get the next sequential filename"""
        pass
    
    @abstractmethod
    def save_image(self, image_content: bytes, filepath: Path) -> bool:
        """Save image content to file"""
        pass

class IDatabaseManager(ABC):
    """Interface for database operations"""
    
    @abstractmethod
    def create_search(self, query: str) -> int:
        """Create a new search entry"""
        pass
    
    @abstractmethod
    def store_urls(self, search_id: int, urls: Set[str]) -> int:
        """Store URLs for a search"""
        pass
    
    @abstractmethod
    def get_unvisited_urls(self, search_id: int, limit: int = 25) -> List[Tuple[int, str]]:
        """Get unvisited URLs"""
        pass
    
    @abstractmethod
    def mark_visited(self, url_id: int, images_found: int, error_msg: str = None):
        """Mark URL as visited"""
        pass
    
    @abstractmethod
    def store_downloaded_image(self, source_url_id: int, image_url: str, image_hash: str, 
                              file_path: str, file_size: int, width: int, height: int,
                              is_human: bool = None, content_type: str = None) -> bool:
        """Store downloaded image metadata"""
        pass
    
    @abstractmethod
    def is_duplicate_image(self, image_hash: str) -> bool:
        """Check if image hash already exists"""
        pass

class ISearchStrategy(ABC):
    """Interface for search strategies"""
    
    @abstractmethod
    def generate_variations(self, base_query: str) -> List[str]:
        """Generate search variations"""
        pass
    
    @abstractmethod
    def should_generate_variations(self, current_count: int, target_count: int) -> bool:
        """Determine if variations should be generated"""
        pass

class IProgressTracker(ABC):
    """Interface for progress tracking"""
    
    @abstractmethod
    def update_progress(self, downloaded: int, target: int, phase: str):
        """Update progress information"""
        pass
    
    @abstractmethod
    def log_activity(self, message: str, level: str = "INFO"):
        """Log activity messages"""
        pass
