"""
Monitoring domain - handles progress tracking and logging.

This package contains functionality for monitoring download progress,
logging activities, and providing user feedback.
"""

from .progress_tracker import ConsoleProgressTracker

__all__ = ["ConsoleProgressTracker"]
