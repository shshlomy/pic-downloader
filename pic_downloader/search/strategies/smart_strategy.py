"""
Search strategy implementation following Single Responsibility Principle
"""

from typing import List
from ...core.interfaces import ISearchStrategy

class SmartSearchStrategy(ISearchStrategy):
    """Smart search strategy that generates variations only when needed"""
    
    def __init__(self, max_variations: int = 12, variation_threshold: int = 3):
        self.max_variations = max_variations
        self.variation_threshold = variation_threshold
    
    def generate_variations(self, base_query: str) -> List[str]:
        """Generate multiple search variations to find more images"""
        variations = []
        
        # Add contextual variations for person searches
        person_contexts = ['singer', 'artist', 'photos', 'pictures', 'portrait', 'red carpet', 'movie', 'actress', 'celebrity', 'professional', 'award', 'fashion', 'beauty', 'style']
        for context in person_contexts:
            variations.append(f"{base_query} {context}")
        
        # Add Hebrew version if it's a Hebrew name
        if any(ord(char) > 127 for char in base_query):  # Contains non-ASCII (likely Hebrew)
            # Already Hebrew, add English contexts
            variations.extend([f"{base_query} זמר", f"{base_query} תמונות"])
        
        # Limit variations to prevent overkill
        return variations[:self.max_variations]
    
    def should_generate_variations(self, current_count: int, target_count: int) -> bool:
        """Determine if variations should be generated"""
        remaining_needed = target_count - current_count
        
        # Be more aggressive for large targets
        if target_count <= 20:
            threshold = 3  # Small targets
        elif target_count <= 100:
            threshold = 5  # Medium targets
        else:
            threshold = 10  # Large targets like 500
        
        # Only generate variations if we need more than the threshold
        # This prevents overkill for small targets
        return remaining_needed > threshold
    
    def get_variation_count(self, remaining_needed: int) -> int:
        """Get the number of variations to generate based on remaining need"""
        if remaining_needed <= 5:
            return 1  # Just one variation for small needs
        elif remaining_needed <= 15:
            return 2  # Two variations for medium needs
        else:
            return min(3, self.max_variations)  # Up to 3 for large needs
    
    def is_hebrew_query(self, query: str) -> bool:
        """Check if query contains Hebrew characters"""
        return any(ord(char) > 127 for char in query)
    
    def get_contextual_variations(self, base_query: str, is_person: bool = True) -> List[str]:
        """Get contextual variations based on query type"""
        if is_person:
            contexts = ['singer', 'artist', 'photos', 'pictures', 'portrait']
        else:
            contexts = ['images', 'photos', 'pictures', 'high quality']
        
        return [f"{base_query} {context}" for context in contexts[:3]]
    
    def get_language_specific_variations(self, base_query: str) -> List[str]:
        """Get language-specific variations"""
        if self.is_hebrew_query(base_query):
            # Hebrew query - add Hebrew contexts
            return [f"{base_query} זמר", f"{base_query} תמונות", f"{base_query} תמונות מקצועיות"]
        else:
            # English query - add English contexts
            return [f"{base_query} professional", f"{base_query} high resolution", f"{base_query} official"]
