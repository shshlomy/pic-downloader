#!/usr/bin/env python3
"""
Utility to clean up duplicate images in downloads folder
"""

import hashlib
import os
import sys
from pathlib import Path
from collections import defaultdict

def calculate_file_hash(filepath):
    """Calculate MD5 hash of file"""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def cleanup_duplicates(folder_path):
    """Remove duplicate images from folder"""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    # Find all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
        image_files.extend(folder.glob(ext))
    
    if not image_files:
        print(f"❌ No image files found in: {folder_path}")
        return
    
    print(f"🔍 Analyzing {len(image_files)} images in: {folder_path}")
    
    # Group files by hash
    hash_to_files = defaultdict(list)
    
    for file_path in image_files:
        try:
            file_hash = calculate_file_hash(file_path)
            hash_to_files[file_hash].append(file_path)
        except Exception as e:
            print(f"⚠️  Error processing {file_path}: {e}")
    
    # Find duplicates
    duplicates_found = 0
    files_removed = 0
    
    for file_hash, files in hash_to_files.items():
        if len(files) > 1:
            duplicates_found += 1
            print(f"\n📋 Duplicate set {duplicates_found} (hash: {file_hash[:12]}...):")
            
            # Sort by filename to keep the first one
            files.sort(key=lambda f: f.name)
            
            # Keep the first file, remove others
            keep_file = files[0]
            print(f"  ✅ Keeping: {keep_file.name}")
            
            for duplicate_file in files[1:]:
                print(f"  🗑️  Removing: {duplicate_file.name}")
                try:
                    duplicate_file.unlink()
                    files_removed += 1
                except Exception as e:
                    print(f"    ❌ Error removing file: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 CLEANUP SUMMARY")
    print(f"{'='*50}")
    print(f"  Total images analyzed: {len(image_files)}")
    print(f"  Duplicate sets found: {duplicates_found}")
    print(f"  Files removed: {files_removed}")
    print(f"  Images remaining: {len(image_files) - files_removed}")
    print(f"{'='*50}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 cleanup_duplicates.py \"folder_path\"")
        print("Example: python3 cleanup_duplicates.py \"downloads/noa kirel\"")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    cleanup_duplicates(folder_path)
