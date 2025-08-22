#!/usr/bin/env python3
"""
Main entry point for the Modular Image Downloader.

This script provides a command-line interface to the image downloader system.
"""

import asyncio
import sys
from pathlib import Path
from pic_downloader.factory import create_image_downloader


async def main():
    """Main entry point for the modular image downloader"""
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <search_query> [max_images]")
        print("Example: python3 main.py 'sarit hadad' 10")
        sys.exit(1)
    
    query = sys.argv[1]
    max_images = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print("=" * 70)
    print("🚀 MODULAR IMAGE DOWNLOADER")
    print("=" * 70)
    print(f"🔧 Configuration:")
    print(f"  • Base Query: '{query}'")
    print(f"  • Max Images: {max_images}")
    print(f"  • Max Workers: 8")
    print(f"  • Architecture: SOLID Principles + Design Patterns")
    print(f"  • Database: SQLite with Foreign Key Constraints")
    print(f"  • Storage: Sequential File Naming")
    print(f"  • Progress: Real-time Tracking with ETA")
    print("=" * 70)
    
    # Create the downloader using the factory
    downloader = create_image_downloader(
        base_query=query,
        max_images=max_images
    )
    
    # Start the download process
    result = await downloader.download_images(query, max_images)
    
    # Display results
    print("\n" + "=" * 70)
    print("📊 DOWNLOAD COMPLETE")
    print("=" * 70)
    
    phases = ["Base", "Remaining", "Variations"]
    for i, phase in enumerate(phases):
        count = result.get(f"phase_{i+1}_downloads", 0)
        print(f"  {phase} Query: {phase} URLs")
        print(f"  Images Downloaded: {count}")
        print(f"  Target: {max_images if i == 0 else 0}")
        print(f"  Total Time: {result.get('total_time', 0):.1f}s")
        if i < len(phases) - 1:
            print("N/A" if count == 0 else f"Success Rate: {(count/max_images)*100:.1f}%")
        print("=" * 70)
    
    print("\n🎯 Download Complete!")
    print(f"  Query: {query}")
    print(f"  Images Downloaded: {result.get('total_downloads', 0)}")
    print(f"  Skipped Duplicates: {result.get('skipped_duplicates', 0)}")
    
    base_count = result.get('phase_1_downloads', 0)
    remaining_count = result.get('phase_2_downloads', 0)
    variations_count = result.get('phase_3_downloads', 0)
    
    print(f"  Details: Base: {base_count}, Remaining: {remaining_count}, Variations: {variations_count}")
    print(f"  Total Time: {result.get('total_time', 0):.1f}s")
    
    total_downloads = result.get('total_downloads', 0)
    total_time = result.get('total_time', 1)  # Avoid division by zero
    
    success_rate = (total_downloads / max_images) * 100 if max_images > 0 else 0
    downloads_per_minute = (total_downloads / total_time) * 60 if total_time > 0 else 0
    
    print(f"  Success Rate: {success_rate:.1f}%")
    print(f"  Downloads/Minute: {downloads_per_minute:.1f}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
