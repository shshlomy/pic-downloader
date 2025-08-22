#!/usr/bin/env python3
"""
Modular Image Downloader - Main Entry Point
Following SOLID principles and design patterns
"""

import asyncio
import sys
from pathlib import Path
from .factory import create_image_downloader

async def main():
    """Main entry point for the modular image downloader"""
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 modular_pic_downloader.py \"search query\" [max_images] [max_workers]")
        print("Example: python3 modular_pic_downloader.py \"sarit hadad\" 20 8")
        sys.exit(1)
    
    # Get arguments
    base_query = sys.argv[1]
    max_images = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    
    print(f"\n{'='*70}")
    print(f"🚀 MODULAR IMAGE DOWNLOADER")
    print(f"{'='*70}")
    print(f"🔧 Configuration:")
    print(f"  • Base Query: '{base_query}'")
    print(f"  • Max Images: {max_images}")
    print(f"  • Max Workers: {max_workers}")
    print(f"  • Architecture: SOLID Principles + Design Patterns")
    print(f"  • Database: SQLite with Foreign Key Constraints")
    print(f"  • Storage: Sequential File Naming")
    print(f"  • Progress: Real-time Tracking with ETA")
    print(f"{'='*70}")
    
    try:
        # Create the image downloader using the factory
        downloader = create_image_downloader(
            base_query=base_query,
            max_images=max_images,
            max_workers=max_workers,
            headless=True,
            db_path="image_sources.db"
        )
        
        # Run the download process
        result = await downloader.download_images(base_query, max_images)
        
        # Display final results
        print(f"\n🎯 Download Complete!")
        print(f"  Query: {result['query']}")
        print(f"  Images Downloaded: {result['downloads']}")
        print(f"  Skipped Duplicates: {result['skipped_duplicates']}")
        print(f"  Details: {result['details']}")
        
        if 'performance_metrics' in result:
            metrics = result['performance_metrics']
            print(f"  Total Time: {metrics.get('total_time', 0):.1f}s")
            print(f"  Success Rate: {metrics.get('success_rate', 0):.1f}%")
            print(f"  Downloads/Minute: {metrics.get('downloads_per_minute', 0):.1f}")
        
        print(f"{'='*70}")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
