"""
Content validation service for image analysis
"""

import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from typing import Tuple, Optional
import logging

class ContentValidator:
    """Content validation service for images"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_models()
    
    def _load_models(self):
        """Load OpenCV models for detection"""
        try:
            # Load pre-trained models for human detection
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
            self.upper_body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_upperbody.xml')
            
            if not all([self.face_cascade, self.body_cascade, self.upper_body_cascade]):
                self.logger.warning("Some OpenCV models failed to load")
                
        except Exception as e:
            self.logger.error(f"Failed to load OpenCV models: {e}")
            self.face_cascade = None
            self.body_cascade = None
            self.upper_body_cascade = None
    
    def validate_image_content(self, image_content: bytes) -> Tuple[bool, str]:
        """
        Validate image content and return (is_human, content_type)
        
        Args:
            image_content: Raw image bytes
            
        Returns:
            Tuple of (is_human, content_type)
        """
        try:
            # Convert bytes to PIL Image
            pil_image = Image.open(BytesIO(image_content))
            
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Check if image contains humans
            is_human = self._detect_humans(cv_image)
            
            # Determine content type
            content_type = self._classify_content_type(cv_image, pil_image)
            
            return is_human, content_type
            
        except Exception as e:
            self.logger.error(f"Content validation failed: {e}")
            return False, "unknown"
    
    def _detect_humans(self, cv_image) -> bool:
        """Detect if image contains humans using OpenCV"""
        if not all([self.face_cascade, self.body_cascade, self.upper_body_cascade]):
            return False  # Can't detect without models
        
        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                return True
            
            # Detect full bodies
            bodies = self.body_cascade.detectMultiScale(gray, 1.1, 4)
            if len(bodies) > 0:
                return True
            
            # Detect upper bodies
            upper_bodies = self.upper_body_cascade.detectMultiScale(gray, 1.1, 4)
            if len(upper_bodies) > 0:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Human detection failed: {e}")
            return False
    
    def _classify_content_type(self, cv_image, pil_image) -> str:
        """Classify the type of content in the image"""
        try:
            # Basic classification based on image characteristics
            height, width = cv_image.shape[:2]
            aspect_ratio = width / height if height > 0 else 1
            
            # Check if it's a logo/graphic (usually square-ish and small)
            if 0.8 <= aspect_ratio <= 1.2 and width < 300:
                return "logo"
            
            # Check if it's a portrait (taller than wide)
            if aspect_ratio < 0.8:
                return "portrait"
            
            # Check if it's a landscape (wider than tall)
            if aspect_ratio > 1.5:
                return "landscape"
            
            # Check if it's a document/text
            if self._is_text_document(cv_image):
                return "document"
            
            # Default to general photo
            return "photo"
            
        except Exception as e:
            self.logger.error(f"Content type classification failed: {e}")
            return "unknown"
    
    def _is_text_document(self, cv_image) -> bool:
        """Check if image appears to be a text document"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Count horizontal and vertical lines (typical in documents)
            horizontal_lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            vertical_lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            # If we have many lines, it's likely a document
            total_lines = (len(horizontal_lines) if horizontal_lines is not None else 0) + \
                         (len(vertical_lines) if vertical_lines is not None else 0)
            
            return total_lines > 10
            
        except Exception:
            return False
    
    def is_human_image(self, image_content: bytes) -> bool:
        """Check if image contains humans (convenience method)"""
        is_human, _ = self.validate_image_content(image_content)
        return is_human
    
    def get_content_type(self, image_content: bytes) -> str:
        """Get content type of image (convenience method)"""
        _, content_type = self.validate_image_content(image_content)
        return content_type
