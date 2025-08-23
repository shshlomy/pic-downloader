"""
Storage manager implementation following Single Responsibility Principle
"""

import hashlib
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image
from io import BytesIO
from ...core.interfaces import IStorageManager

class SequentialStorageManager(IStorageManager):
    """Storage manager for sequential file naming and image saving"""
    
    def __init__(self, base_download_dir: Path, base_subject: str, database_manager=None):
        self.base_download_dir = base_download_dir
        self.base_subject = base_subject
        self.download_dir = base_download_dir / base_subject
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.database_manager = database_manager  # 🚨 NEW: Add database manager reference
        self._initialize_file_counter()
    
    def _initialize_file_counter(self):
        """Initialize the file counter based on existing files"""
        existing_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
            existing_files.extend(self.download_dir.glob(ext))
        
        if existing_files:
            # Extract numbers from existing filenames
            numbers = []
            for file in existing_files:
                try:
                    # Extract number from filename like "001.jpg"
                    number_str = file.stem
                    if number_str.isdigit():
                        numbers.append(int(number_str))
                except (ValueError, AttributeError):
                    continue
            
            if numbers:
                self.next_file_number = max(numbers) + 1
            else:
                self.next_file_number = 0
        else:
            self.next_file_number = 0
    
    def get_next_filename(self, image_url: str, format: str) -> Tuple[str, Path]:
        """Get the next sequential filename"""
        # Determine file extension
        if format.lower() in ['jpeg', 'jpg']:
            ext = 'jpg'
        elif format.lower() == 'png':
            ext = 'png'
        elif format.lower() == 'webp':
            ext = 'webp'
        else:
            ext = 'jpg'  # Default to jpg
        
        # Generate sequential filename
        filename = f"{self.next_file_number:03d}.{ext}"
        filepath = self.download_dir / filename
        
        self.next_file_number += 1
        return filename, filepath
    
    def save_image(self, image_content: bytes, filepath: Path) -> bool:
        """Save image content to file"""
        try:
            # Open image from bytes
            img = Image.open(BytesIO(image_content))
            
            # Save with high quality
            img.save(filepath, quality=95)
            return True
            
        except Exception as e:
            print(f"    ❌ Error saving image: {e}")
            return False
    
    def calculate_image_hash(self, image_content: bytes) -> str:
        """Calculate MD5 hash of image content"""
        return hashlib.md5(image_content).hexdigest()
    
    def is_duplicate_content(self, image_hash: str) -> bool:
        """🚨 NEW: Check if image content already exists in database"""
        if self.database_manager:
            return self.database_manager.is_duplicate_image(image_hash)
        return False
    
    def get_image_dimensions(self, image_content: bytes) -> Tuple[Optional[int], Optional[int]]:
        """Get image dimensions from content"""
        try:
            img = Image.open(BytesIO(image_content))
            return img.size
        except Exception:
            return None, None
    
    def validate_image(self, image_content: bytes, min_width: int = 150, min_height: int = 150, min_size: int = 8000) -> bool:
        """Validate image meets minimum requirements"""
        if len(image_content) < min_size:
            return False
        
        try:
            img = Image.open(BytesIO(image_content))
            width, height = img.size
            
            if width < min_width or height < min_height:
                return False
                
            return True
            
        except Exception:
            return False
    
    def cleanup_failed_download(self, filepath: Path):
        """Clean up failed download file"""
        try:
            if filepath.exists():
                filepath.unlink()
        except Exception:
            pass  # Ignore cleanup errors
