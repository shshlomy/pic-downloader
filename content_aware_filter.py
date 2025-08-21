#!/usr/bin/env python3
"""
Content-Aware Image Filtering System
Advanced filtering using computer vision and machine learning techniques
"""

import cv2
import numpy as np
import mediapipe as mp
from PIL import Image
from io import BytesIO
import requests
import logging
from typing import Tuple, Optional, Dict, Any
from urllib.parse import urlparse
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentAwareFilter:
    """Advanced image filtering using computer vision and ML"""
    
    def __init__(self):
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.3
        )
        
        # Initialize OpenCV face cascade as backup
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except:
            logger.warning("OpenCV face cascade not available")
            self.face_cascade = None
        
        # Content type patterns for better filtering
        self.MUSIC_DOMAINS = {
            'genius.com', 'spotify.com', 'apple.com', 'music.apple.com',
            'deezer.com', 'soundcloud.com', 'last.fm', 'shazam.com',
            'amazon.com', 'bandcamp.com', 'discogs.com'
        }
        
        self.CDN_PATTERNS = [
            r'cdn[-_]?images?', r'i\.ytimg', r'mzstatic', r'cloudfront',
            r'amazonaws', r'googleusercontent', r'fbcdn', r'cdninstagram'
        ]
        
        # Enhanced irrelevant patterns
        self.IRRELEVANT_PATTERNS = [
            # UI Elements
            r'logo', r'icon', r'favicon', r'sprite', r'button', r'arrow', r'nav',
            r'menu', r'header', r'footer', r'sidebar', r'banner', r'ad[_-]',
            r'placeholder', r'loading', r'spinner', r'blank', r'default',
            
            # Music specific irrelevant
            r'album[-_]?cover', r'artwork', r'vinyl', r'cd[-_]?cover',
            r'playlist', r'track[-_]?art', r'single[-_]?cover',
            
            # Generic irrelevant
            r'thumbnail', r'thumb', r'preview', r'watermark',
            r'background', r'bg[-_]?image', r'pattern', r'texture',
            
            # Size indicators for small images
            r'(?:^|[/_-])(?:16|24|32|48|64|96|128)(?:x(?:16|24|32|48|64|96|128))?(?:[/_-]|$)',
            
            # Wikipedia/Wikimedia
            r'wikipedia.*logo', r'wikimedia.*logo', r'commons.*logo'
        ]
    
    def analyze_image_content(self, image_data: bytes, img_url: str = "", query: str = "") -> Dict[str, Any]:
        """
        Comprehensive image content analysis
        Returns analysis results with confidence scores
        """
        try:
            # Convert to PIL Image
            pil_image = Image.open(BytesIO(image_data))
            
            # Convert to OpenCV format
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            analysis = {
                'has_faces': False,
                'face_count': 0,
                'face_confidence': 0.0,
                'is_portrait': False,
                'aspect_ratio': 0.0,
                'dominant_colors': [],
                'content_type': 'unknown',
                'relevance_score': 0.0,
                'reasons': []
            }
            
            # Basic image properties
            height, width = cv_image.shape[:2]
            analysis['aspect_ratio'] = width / height if height > 0 else 0
            analysis['is_portrait'] = 0.7 <= analysis['aspect_ratio'] <= 1.4  # Portrait-like ratio
            
            # Face detection with MediaPipe
            face_results = self._detect_faces_mediapipe(cv_image)
            if face_results:
                analysis.update(face_results)
            elif self.face_cascade:
                # Fallback to OpenCV
                face_results = self._detect_faces_opencv(cv_image)
                analysis.update(face_results)
            
            # Content type analysis
            analysis['content_type'] = self._classify_content_type(img_url, analysis)
            
            # Calculate relevance score
            analysis['relevance_score'] = self._calculate_relevance_score(
                analysis, img_url, query
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing image content: {e}")
            return {
                'has_faces': False,
                'face_count': 0,
                'face_confidence': 0.0,
                'is_portrait': False,
                'aspect_ratio': 0.0,
                'content_type': 'unknown',
                'relevance_score': 0.1,  # Low score for failed analysis
                'reasons': [f'Analysis failed: {str(e)}']
            }
    
    def _detect_faces_mediapipe(self, cv_image: np.ndarray) -> Dict[str, Any]:
        """Detect faces using MediaPipe"""
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_image)
            
            face_data = {
                'has_faces': False,
                'face_count': 0,
                'face_confidence': 0.0,
                'reasons': []
            }
            
            if results.detections:
                face_data['has_faces'] = True
                face_data['face_count'] = len(results.detections)
                
                # Get average confidence
                confidences = [detection.score[0] for detection in results.detections]
                face_data['face_confidence'] = sum(confidences) / len(confidences)
                
                face_data['reasons'].append(f"MediaPipe detected {face_data['face_count']} face(s) with avg confidence {face_data['face_confidence']:.2f}")
            
            return face_data
            
        except Exception as e:
            logger.error(f"MediaPipe face detection error: {e}")
            return {'has_faces': False, 'face_count': 0, 'face_confidence': 0.0, 'reasons': []}
    
    def _detect_faces_opencv(self, cv_image: np.ndarray) -> Dict[str, Any]:
        """Detect faces using OpenCV as fallback"""
        try:
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            
            face_data = {
                'has_faces': len(faces) > 0,
                'face_count': len(faces),
                'face_confidence': 0.8 if len(faces) > 0 else 0.0,  # OpenCV doesn't provide confidence
                'reasons': []
            }
            
            if len(faces) > 0:
                face_data['reasons'].append(f"OpenCV detected {len(faces)} face(s)")
            
            return face_data
            
        except Exception as e:
            logger.error(f"OpenCV face detection error: {e}")
            return {'has_faces': False, 'face_count': 0, 'face_confidence': 0.0, 'reasons': []}
    
    def _classify_content_type(self, img_url: str, analysis: Dict[str, Any]) -> str:
        """Classify the type of content based on URL and analysis"""
        url_lower = img_url.lower()
        
        # Check for music-related content
        domain = urlparse(img_url).netloc.lower()
        if any(music_domain in domain for music_domain in self.MUSIC_DOMAINS):
            if analysis['has_faces']:
                return 'music_artist_photo'
            else:
                return 'music_artwork'
        
        # Check for CDN patterns (often non-person content)
        if any(re.search(pattern, url_lower) for pattern in self.CDN_PATTERNS):
            if analysis['has_faces']:
                return 'cdn_person_photo'
            else:
                return 'cdn_media'
        
        # Check for irrelevant patterns
        if any(re.search(pattern, url_lower) for pattern in self.IRRELEVANT_PATTERNS):
            return 'irrelevant_ui'
        
        # Classify based on face detection
        if analysis['has_faces']:
            if analysis['is_portrait']:
                return 'portrait_photo'
            else:
                return 'group_photo'
        
        return 'unknown_content'
    
    def _calculate_relevance_score(self, analysis: Dict[str, Any], img_url: str, query: str) -> float:
        """Calculate relevance score based on multiple factors"""
        score = 0.0
        reasons = []
        
        # Face detection bonus (most important for person searches)
        if analysis['has_faces']:
            face_bonus = min(0.6, analysis['face_confidence'] * 0.6)
            score += face_bonus
            reasons.append(f"Face detection: +{face_bonus:.2f}")
            
            # Extra bonus for single face (likely the person we're looking for)
            if analysis['face_count'] == 1:
                score += 0.2
                reasons.append("Single face: +0.2")
        else:
            score -= 0.3  # Penalty for no faces when searching for a person
            reasons.append("No faces detected: -0.3")
        
        # Portrait orientation bonus
        if analysis['is_portrait']:
            score += 0.15
            reasons.append("Portrait orientation: +0.15")
        
        # Content type scoring
        content_type = analysis['content_type']
        if content_type == 'portrait_photo':
            score += 0.25
            reasons.append("Portrait photo: +0.25")
        elif content_type == 'music_artist_photo':
            score += 0.2
            reasons.append("Music artist photo: +0.2")
        elif content_type == 'group_photo':
            score += 0.1
            reasons.append("Group photo: +0.1")
        elif content_type in ['music_artwork', 'cdn_media', 'irrelevant_ui']:
            score -= 0.4
            reasons.append(f"{content_type}: -0.4")
        
        # URL pattern penalties
        url_lower = img_url.lower()
        if any(re.search(pattern, url_lower) for pattern in self.IRRELEVANT_PATTERNS):
            score -= 0.3
            reasons.append("Irrelevant URL pattern: -0.3")
        
        # Size-based adjustments (from image dimensions)
        try:
            # We can't get dimensions here without re-processing, so we'll estimate from URL
            size_match = re.search(r'(\d+)x(\d+)', url_lower)
            if size_match:
                width, height = int(size_match.group(1)), int(size_match.group(2))
                if width < 150 or height < 150:
                    score -= 0.2
                    reasons.append("Small dimensions: -0.2")
                elif width >= 400 and height >= 400:
                    score += 0.1
                    reasons.append("Good dimensions: +0.1")
        except:
            pass
        
        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))
        
        analysis['reasons'].extend(reasons)
        
        return score
    
    def is_relevant_image(self, image_data: bytes, img_url: str = "", query: str = "", 
                         min_relevance_score: float = 0.4) -> Tuple[bool, Dict[str, Any]]:
        """
        Main filtering function - determines if image is relevant
        
        Args:
            image_data: Raw image bytes
            img_url: Image URL for context
            query: Search query (person name)
            min_relevance_score: Minimum score threshold
            
        Returns:
            (is_relevant, analysis_results)
        """
        analysis = self.analyze_image_content(image_data, img_url, query)
        is_relevant = analysis['relevance_score'] >= min_relevance_score
        
        logger.info(f"Image relevance: {analysis['relevance_score']:.2f} ({'PASS' if is_relevant else 'REJECT'}) - {img_url[:100]}...")
        if analysis['reasons']:
            logger.debug(f"Reasoning: {'; '.join(analysis['reasons'])}")
        
        return is_relevant, analysis
    
    def quick_url_filter(self, img_url: str) -> bool:
        """
        Quick URL-based filtering before downloading
        Returns False if definitely irrelevant, True if might be relevant
        """
        url_lower = img_url.lower()
        
        # Quick reject for obvious irrelevant patterns
        quick_reject_patterns = [
            r'logo', r'icon', r'favicon', r'sprite', r'button',
            r'(?:^|[/_-])(?:16|24|32|48|64|96)(?:x(?:16|24|32|48|64|96))?(?:[/_-]|$)',  # Small sizes
            r'ad[_-]', r'banner', r'header', r'footer'
        ]
        
        for pattern in quick_reject_patterns:
            if re.search(pattern, url_lower):
                return False
        
        return True  # Might be relevant, needs content analysis

# Global instance
content_filter = ContentAwareFilter()
