"""
Factory domain - handles component creation and dependency injection.

This package contains factory classes and configuration management
for creating and wiring all system components.
"""

from .component_factory import ImageDownloaderFactory, create_image_downloader

__all__ = [
    "ImageDownloaderFactory",
    "create_image_downloader"
]
