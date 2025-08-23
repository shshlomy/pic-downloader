"""
Factory class for creating and wiring all components together
Following Factory Pattern and Dependency Injection principles
"""

from pathlib import Path
from ..core.interfaces import (
    ISearchProvider, IImageExtractor, IImageDownloader, 
    IContentFilter, IStorageManager, IDatabaseManager, 
    ISearchStrategy, IProgressTracker
)
from ..search.providers.google_provider import GoogleSearchProvider
from ..extraction.web_extractor import WebImageExtractor
from ..download.http_downloader import HTTPImageDownloader
from ..storage.managers.sequential_manager import SequentialStorageManager
from ..storage.database.sqlite_manager import SQLiteDatabaseManager
from ..search.strategies.smart_strategy import SmartSearchStrategy
from ..monitoring.progress_tracker import ConsoleProgressTracker
from ..core.orchestrator import ImageDownloadOrchestrator
from ..config.settings import ConfigurationManager

class ImageDownloaderFactory:
    """Factory for creating and configuring image downloader components"""
    
    @staticmethod
    def create_search_provider(headless: bool = True, timeout: int = 30000) -> ISearchProvider:
        """Create a Google search provider"""
        return GoogleSearchProvider(headless=headless, timeout=timeout)
    
    @staticmethod
    def create_image_extractor(headless: bool = True, timeout: int = 30000) -> IImageExtractor:
        """Create a website image extractor"""
        return WebImageExtractor(headless=headless, timeout=timeout)
    
    @staticmethod
    def create_storage_manager(base_download_dir: Path, base_subject: str, database_manager=None) -> IStorageManager:
        """Create a sequential storage manager with database manager reference"""
        return SequentialStorageManager(base_download_dir, base_subject, database_manager)
    
    @staticmethod
    def create_database_manager(db_path: str = "image_sources.db") -> IDatabaseManager:
        """Create a SQLite database manager"""
        return SQLiteDatabaseManager(db_path)
    
    @staticmethod
    def create_search_strategy(max_variations: int = 4, variation_threshold: int = 3) -> ISearchStrategy:
        """Create a smart search strategy"""
        return SmartSearchStrategy(max_variations=max_variations, variation_threshold=variation_threshold)
    
    @staticmethod
    def create_progress_tracker() -> IProgressTracker:
        """Create a console progress tracker"""
        return ConsoleProgressTracker()
    
    @staticmethod
    def create_image_downloader(
        storage_manager: IStorageManager, 
        content_filter, 
        timeout: int = 15
    ) -> IImageDownloader:
        """Create an HTTP image downloader"""
        return HTTPImageDownloader(storage_manager, content_filter, timeout)
    
    @staticmethod
    def create_orchestrator(
        base_query: str,
        max_images: int = 100,
        max_workers: int = 8,
        headless: bool = True,
        db_path: str = "image_sources.db",
        config=None
    ) -> ImageDownloadOrchestrator:
        """Create a fully configured image download orchestrator"""
        
        # Extract base subject for folder name
        base_subject = ImageDownloaderFactory._extract_base_subject(base_query)
        
        # Create all components
        search_provider = ImageDownloaderFactory.create_search_provider(headless=headless)
        progress_tracker = ImageDownloaderFactory.create_progress_tracker()
        # Create image extractor
        image_extractor = WebImageExtractor(
            progress_tracker=progress_tracker,
            headless=headless,
            timeout=30000
        )
        database_manager = ImageDownloaderFactory.create_database_manager(db_path)
        storage_manager = ImageDownloaderFactory.create_storage_manager(Path("downloads"), base_subject, database_manager)
        search_strategy = ImageDownloaderFactory.create_search_strategy()
        progress_tracker = ImageDownloaderFactory.create_progress_tracker()
        
        # Import content filter (assuming it exists)
        try:
            from content_aware_filter import content_filter
        except ImportError:
            # Create a dummy content filter if the real one doesn't exist
            content_filter = DummyContentFilter()
        
        image_downloader = ImageDownloaderFactory.create_image_downloader(
            storage_manager, content_filter
        )
        
        # Create configuration
        config = ConfigurationManager()
        
        # Create and return orchestrator
        return ImageDownloadOrchestrator(
            search_provider=search_provider,
            image_extractor=image_extractor,
            image_downloader=image_downloader,
            content_filter=content_filter,
            storage_manager=storage_manager,
            database_manager=database_manager,
            search_strategy=search_strategy,
            progress_tracker=progress_tracker,
            max_workers=max_workers,
            config=config
        )
    
    @staticmethod
    def _extract_base_subject(query: str) -> str:
        """Extract the main subject from search query"""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = query.lower().split()
        filtered_words = []
        
        for word in words:
            if word not in stop_words and len(word) > 1:
                filtered_words.append(word)
        
        # Take first 1-2 meaningful words
        base_subject = ' '.join(filtered_words[:2]) if filtered_words else query
        return base_subject

class DummyContentFilter:
    """Dummy content filter for when the real one is not available"""
    
    def is_relevant_image(self, image_content: bytes, image_url: str, query: str, min_score: float = 0.4):
        """Always return True for dummy filter"""
        return True, {"score": 1.0, "reason": "Dummy filter - always relevant"}
    
    def quick_url_filter(self, image_url: str) -> bool:
        """Always return True for dummy filter"""
        return True

class ConfigurationManager:
    """Configuration manager for the image downloader system"""
    
    def __init__(self):
        self.config = {
            "headless": True,
            "timeout": 30000,
            "max_workers": 8,
            "db_path": "image_sources.db",
            "download_dir": "downloads",
            "max_variations": 4,
            "variation_threshold": 3,
            "image_timeout": 15,
            "min_image_width": 150,
            "min_image_height": 150,
            "min_image_size": 8000
        }
    
    def get_config(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value):
        """Set configuration value"""
        self.config[key] = value
    
    def update_config(self, new_config: dict):
        """Update multiple configuration values"""
        self.config.update(new_config)
    
    def get_all_config(self) -> dict:
        """Get all configuration values"""
        return self.config.copy()

# Convenience function for easy usage
def create_image_downloader(
    base_query: str,
    max_images: int = 100,
    max_workers: int = 8,
    headless: bool = True,
    db_path: str = "image_sources.db"
) -> ImageDownloadOrchestrator:
    """Convenience function to create a configured image downloader"""
    return ImageDownloaderFactory.create_orchestrator(
        base_query=base_query,
        max_images=max_images,
        max_workers=max_workers,
        headless=headless,
        db_path=db_path
    )
