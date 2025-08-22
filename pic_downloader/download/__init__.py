"""
Download domain - handles actual image downloading.

This package contains functionality for downloading images
from URLs using various protocols and methods.
"""

from .http_downloader import HTTPImageDownloader

__all__ = ["HTTPImageDownloader"]
