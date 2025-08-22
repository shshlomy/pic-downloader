"""
Core domain models, interfaces, and orchestration logic.

This package contains the fundamental abstractions and coordination logic
that define the image downloading domain.
"""

from .interfaces import (
    # Data classes
    SearchResult, ImageTask, DownloadResult,
    
    # Core interfaces
    ISearchProvider, IImageExtractor, IImageDownloader,
    IContentFilter, IStorageManager, IDatabaseManager,
    ISearchStrategy, IProgressTracker
)

from .orchestrator import ImageDownloadOrchestrator

__all__ = [
    # Data classes
    "SearchResult", "ImageTask", "DownloadResult",
    
    # Interfaces
    "ISearchProvider", "IImageExtractor", "IImageDownloader",
    "IContentFilter", "IStorageManager", "IDatabaseManager", 
    "ISearchStrategy", "IProgressTracker",
    
    # Orchestrator
    "ImageDownloadOrchestrator"
]
