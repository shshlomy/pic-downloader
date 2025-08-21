#!/usr/bin/env python3
"""
Main Picture Downloader Script - Uses consolidated downloader
"""

import sys
import asyncio
from consolidated_downloader import ConsolidatedDownloader

def main():
    """Main entry point for the picture downloader"""
    if len(sys.argv) < 2:
        print("🖼️  Advanced Image Downloader")
        print("=" * 40)
        print("Usage: python3 pic_downloader.py \"search query\" [max_images] [max_workers]")
        print("\nExamples:")
        print("  python3 pic_downloader.py \"michael jordan\"")
        print("  python3 pic_downloader.py \"noa kirel\" 50")
        print("  python3 pic_downloader.py \"kobe bryant\" 100 8")
        print("\nFeatures:")
        print("  • Consolidated folders (all searches for same subject in one folder)")
        print("  • Fixed duplicate detection")
        print("  • Enhanced image filtering")
        print("  • Multi-threaded downloading")
        print("  • Persistent database tracking")
        sys.exit(1)
    
    query = sys.argv[1]
    max_images = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    # Run the consolidated downloader
    downloader = ConsolidatedDownloader(query, max_images, max_workers)
    asyncio.run(downloader.run())

if __name__ == "__main__":
    main()
