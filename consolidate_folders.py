#!/usr/bin/env python3
"""
Utility to consolidate multiple folders for the same subject into one folder
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path
from collections import defaultdict

def consolidate_subject_folders(base_subject: str):
    """Consolidate all folders for a subject into one main folder"""
    
    downloads_dir = Path("downloads")
    
    if not downloads_dir.exists():
        print("❌ Downloads directory not found")
        return
    
    # Find all folders that start with the base subject
    subject_folders = []
    main_folder = None
    
    for folder in downloads_dir.iterdir():
        if folder.is_dir():
            folder_name = folder.name.lower()
            base_lower = base_subject.lower()
            
            if folder_name == base_lower:
                main_folder = folder
            elif folder_name.startswith(base_lower + " "):
                subject_folders.append(folder)
    
    if not main_folder:
        # Create main folder
        main_folder = downloads_dir / base_subject
        main_folder.mkdir(exist_ok=True)
        print(f"📁 Created main folder: {main_folder}")
    
    if not subject_folders:
        print(f"✅ No additional folders found for '{base_subject}'")
        return
    
    print(f"🔍 Found {len(subject_folders)} folders to consolidate:")
    for folder in subject_folders:
        print(f"  📂 {folder.name}")
    
    print(f"\n📁 Consolidating into: {main_folder.name}")
    
    # Track hashes to avoid duplicates during consolidation
    existing_hashes = set()
    
    # Get hashes of existing files in main folder
    for file_path in main_folder.glob("*.jpg"):
        existing_hashes.add(_get_file_hash(file_path))
    for file_path in main_folder.glob("*.jpeg"):
        existing_hashes.add(_get_file_hash(file_path))
    for file_path in main_folder.glob("*.png"):
        existing_hashes.add(_get_file_hash(file_path))
    for file_path in main_folder.glob("*.webp"):
        existing_hashes.add(_get_file_hash(file_path))
    
    print(f"📊 Main folder has {len(existing_hashes)} existing unique images")
    
    # Get next available number
    existing_files = list(main_folder.glob("*.jpg")) + \
                    list(main_folder.glob("*.jpeg")) + \
                    list(main_folder.glob("*.png")) + \
                    list(main_folder.glob("*.webp"))
    next_num = len(existing_files)
    
    moved_count = 0
    skipped_count = 0
    
    # Process each subject folder
    for folder in subject_folders:
        print(f"\n📂 Processing: {folder.name}")
        
        # Get all image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif']:
            image_files.extend(folder.glob(ext))
        
        print(f"  Found {len(image_files)} images")
        
        for image_file in image_files:
            try:
                # Calculate hash
                file_hash = _get_file_hash(image_file)
                
                # Check if already exists
                if file_hash in existing_hashes:
                    skipped_count += 1
                    print(f"    ⏭️  Skipped duplicate: {image_file.name}")
                    continue
                
                # Move to main folder with new name
                extension = image_file.suffix
                new_name = f"{next_num:03d}_{image_file.stem.split('_', 1)[-1]}{extension}"
                new_path = main_folder / new_name
                
                shutil.move(str(image_file), str(new_path))
                existing_hashes.add(file_hash)
                moved_count += 1
                next_num += 1
                
                print(f"    ✅ Moved: {image_file.name} → {new_name}")
                
            except Exception as e:
                print(f"    ❌ Error moving {image_file.name}: {e}")
        
        # Remove empty folder
        try:
            if not any(folder.iterdir()):
                folder.rmdir()
                print(f"  🗑️  Removed empty folder: {folder.name}")
            else:
                print(f"  ⚠️  Folder not empty, keeping: {folder.name}")
        except Exception as e:
            print(f"  ⚠️  Could not remove folder: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 CONSOLIDATION COMPLETE")
    print(f"{'='*50}")
    print(f"  Subject: {base_subject}")
    print(f"  Main folder: {main_folder.name}")
    print(f"  Images moved: {moved_count}")
    print(f"  Duplicates skipped: {skipped_count}")
    print(f"  Total images in main folder: {len(list(main_folder.glob('*.jpg')) + list(main_folder.glob('*.jpeg')) + list(main_folder.glob('*.png')) + list(main_folder.glob('*.webp')))}")
    print(f"{'='*50}")

def _get_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of file"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 consolidate_folders.py \"base_subject\"")
        print("Example: python3 consolidate_folders.py \"noa kirel\"")
        sys.exit(1)
    
    base_subject = sys.argv[1]
    consolidate_subject_folders(base_subject)
