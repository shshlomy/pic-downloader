#!/usr/bin/env python3
"""
Test Content-Aware Filtering System
Tests the new filtering against existing problematic images
"""

import sys
import os
from pathlib import Path
from content_aware_filter import content_filter
import requests
from urllib.parse import urlparse

def test_existing_images(folder_path: str, query: str = ""):
    """Test content filtering on existing downloaded images"""
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    # Find image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
        image_files.extend(folder.glob(ext))
    
    if not image_files:
        print(f"❌ No image files found in: {folder_path}")
        return
    
    print(f"🔍 Testing content filter on {len(image_files)} images from: {folder_path}")
    print(f"   Query context: '{query}'")
    print(f"{'='*80}")
    
    # Test each image
    relevant_count = 0
    irrelevant_count = 0
    error_count = 0
    
    # Sort by filename for consistent testing
    image_files.sort(key=lambda x: x.name)
    
    for i, image_file in enumerate(image_files[:20]):  # Test first 20 images
        try:
            # Read image data
            with open(image_file, 'rb') as f:
                image_data = f.read()
            
            # Extract domain from filename (format: ###_domain.ext)
            filename_parts = image_file.stem.split('_', 1)
            domain = filename_parts[1] if len(filename_parts) > 1 else "unknown"
            fake_url = f"https://{domain.replace('_', '.')}/image.jpg"
            
            # Test content filtering
            is_relevant, analysis = content_filter.is_relevant_image(
                image_data, fake_url, query, min_relevance_score=0.4
            )
            
            status = "✅ RELEVANT" if is_relevant else "🚫 IRRELEVANT"
            score = analysis['relevance_score']
            content_type = analysis['content_type']
            
            print(f"{i+1:2d}. {image_file.name[:50]:<50} {status} (score: {score:.2f}) - {content_type}")
            
            # Show face detection info
            if analysis.get('has_faces'):
                print(f"    👤 Faces: {analysis['face_count']} (confidence: {analysis['face_confidence']:.2f})")
            
            # Show top reasons
            if analysis.get('reasons') and len(analysis['reasons']) > 0:
                print(f"    📝 {analysis['reasons'][0]}")
            
            if is_relevant:
                relevant_count += 1
            else:
                irrelevant_count += 1
                
        except Exception as e:
            print(f"{i+1:2d}. {image_file.name[:50]:<50} ❌ ERROR: {str(e)[:30]}...")
            error_count += 1
    
    print(f"\n{'='*80}")
    print(f"📊 FILTERING TEST RESULTS")
    print(f"{'='*80}")
    print(f"  Total images tested: {len(image_files[:20])}")
    print(f"  Relevant (would keep): {relevant_count}")
    print(f"  Irrelevant (would reject): {irrelevant_count}")
    print(f"  Errors: {error_count}")
    print(f"  Filtering effectiveness: {irrelevant_count/(relevant_count + irrelevant_count)*100:.1f}% rejected")
    print(f"{'='*80}")

def test_url_filtering():
    """Test quick URL filtering on known problematic URLs"""
    print(f"\n🔍 Testing Quick URL Filtering")
    print(f"{'='*50}")
    
    test_urls = [
        # Should be rejected (irrelevant)
        "https://cdn-images.dzcdn.net/album-cover.jpg",
        "https://i.ytimg.com/vi/abc123/maxresdefault.jpg", 
        "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/logo.jpg",
        "https://example.com/32x32/icon.png",
        "https://example.com/favicon.ico",
        "https://example.com/sprite-sheet.png",
        "https://example.com/ad_banner.jpg",
        
        # Should pass quick filter (might be relevant)
        "https://example.com/artist-photo.jpg",
        "https://cdn.example.com/person-image-500x600.jpg",
        "https://images.example.com/celebrity-portrait.png",
        "https://media.example.com/singer-photo.webp",
    ]
    
    for url in test_urls:
        result = content_filter.quick_url_filter(url)
        status = "✅ PASS" if result else "🚫 REJECT"
        print(f"  {status} {url}")
    
    print(f"{'='*50}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_content_filter.py \"folder_path\" [query]")
        print("Example: python3 test_content_filter.py \"downloads/agam buhbut\" \"agam buhbut\"")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    query = sys.argv[2] if len(sys.argv) > 2 else ""
    
    # Test URL filtering first
    test_url_filtering()
    
    # Test content filtering on existing images
    test_existing_images(folder_path, query)

if __name__ == "__main__":
    main()
