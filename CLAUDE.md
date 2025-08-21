# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an advanced multi-threaded image downloader that extracts original website URLs from Google Images and downloads high-quality images with fixed duplicate detection. The system uses SQLite for persistent tracking and supports Unicode/Hebrew search queries.

## Core Architecture

### Main Components

- **`pic_downloader.py`** - Main entry point and CLI interface
- **`comprehensive_downloader_fixed.py`** - Core downloader engine with fixes for duplicate detection
- **`cleanup_duplicates.py`** - Utility for removing existing duplicates based on content hashes
- **`analyze_visit_buttons.py`** - Debug tool for analyzing URL extraction from Google Images
- **`image_sources.db`** - SQLite database for tracking searches, URLs, and downloaded images

### Key Classes

- **`FixedMultiThreadedDownloader`** - Main downloader class implementing async/await and threading
- **`FixedURLDatabase`** - Database interface for persistent storage
- **Hash-based duplicate detection** - Uses MD5 of final saved file content (not raw download)

### Critical Fixes Implemented

1. **Duplicate Detection Bug Fix**: Hash calculation moved to AFTER PIL processing of saved files
2. **Enhanced Image Filtering**: Improved filtering of logos, icons, and irrelevant UI elements
3. **Unicode Support**: Full support for Hebrew and other Unicode search queries

## Development Commands

### Setup
```bash
# Install dependencies and Playwright browsers
python setup.py
```

### Running the Application
```bash
# Basic usage
python pic_downloader.py "search query"

# With custom parameters
python pic_downloader.py "search query" [max_images] [max_workers]

# Examples
python pic_downloader.py "michael jordan" 50 8
python pic_downloader.py "נועה קירל" 30 5  # Hebrew support
```

### Testing
```bash
# Test Hebrew/Unicode functionality
python test_hebrew.py

# Clean up duplicates in existing folders
python cleanup_duplicates.py "downloads/folder_name"

# Debug URL extraction
python analyze_visit_buttons.py
```

### Database Operations
```bash
# View statistics
sqlite3 image_sources.db "SELECT COUNT(DISTINCT image_hash) FROM downloaded_images;"
sqlite3 image_sources.db "SELECT query, total_urls FROM searches;"
```

## Database Schema

- **searches**: Query tracking with timestamps and URL counts
- **source_urls**: Original website URLs with visit status and error tracking  
- **downloaded_images**: Image metadata with MD5 hashes for duplicate detection

The `image_hash` field in `downloaded_images` is UNIQUE and calculated from the final saved file content after PIL processing.

## Threading Architecture

- Uses `asyncio` for concurrent website visiting
- `ThreadPoolExecutor` for parallel image downloading
- Thread-safe database operations with proper locking
- Default 5 workers, configurable up to 8+ for better performance

## File Organization

- Downloads saved to `downloads/{search_query}/` with sanitized filenames
- Images numbered sequentially (000_, 001_, etc.) with domain prefixes
- SQLite database tracks all operations for resume capability and duplicate prevention

## Dependencies

Core packages: `playwright`, `aiohttp`, `Pillow`, `requests`
- Playwright requires browser installation via `python setup.py`
- All dependencies specified in `requirements.txt`