"""
Configuration management for the image downloader system.
"""

from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class DownloadConfig:
    """Configuration for download operations"""
    max_workers: int = 8
    timeout: int = 30000
    headless: bool = True
    max_variations: int = 4
    variation_threshold: int = 3
    

@dataclass
class StorageConfig:
    """Configuration for storage operations"""
    base_download_dir: Path = Path("downloads")
    db_path: str = "image_sources.db"
    

@dataclass
class SearchConfig:
    """Configuration for search operations"""
    max_urls_per_search: int = 25
    early_termination_buffer: int = 5
    parallel_url_processing: int = 5  # Number of URLs to process simultaneously
    page_load_timeout: int = 500  # Milliseconds to wait for page load
    

class ConfigurationManager:
    """Centralized configuration management"""
    
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
            "min_image_size": 8000,
            "parallel_url_processing": 10,  # Increased from 5 to 10
            "page_load_timeout": 300,  # Reduced from 500ms to 300ms
            "connection_pool_size": 20,  # New: Connection pooling
            "max_retries": 3,  # New: Max retries for failed requests
            "smart_prioritization": True,  # New: Enable smart URL prioritization
            "fast_domain_timeout": 200,  # New: Faster timeout for known fast domains
            "slow_domain_timeout": 800,  # New: Slower timeout for known slow domains
        }
    
    def update_from_dict(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        if "download" in config_dict:
            for key, value in config_dict["download"].items():
                if hasattr(self.download, key):
                    setattr(self.download, key, value)
        
        if "storage" in config_dict:
            for key, value in config_dict["storage"].items():
                if hasattr(self.storage, key):
                    setattr(self.storage, key, value)
        
        if "search" in config_dict:
            for key, value in config_dict["search"].items():
                if hasattr(self.search, key):
                    setattr(self.search, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "download": {
                "max_workers": self.download.max_workers,
                "timeout": self.download.timeout,
                "headless": self.download.headless,
                "max_variations": self.download.max_variations,
                "variation_threshold": self.download.variation_threshold,
            },
            "storage": {
                "base_download_dir": str(self.storage.base_download_dir),
                "db_path": self.storage.db_path,
            },
            "search": {
                "max_urls_per_search": self.search.max_urls_per_search,
                "early_termination_buffer": self.search.early_termination_buffer,
            }
        }
