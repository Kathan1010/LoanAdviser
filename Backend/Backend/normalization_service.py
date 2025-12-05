"""
Text Normalization and Transliteration Service

This module handles:
- Text cleaning (remove extra spaces, normalize punctuation)
- Transliteration (Hinglish to Devanagari, Roman to native scripts)
- Number normalization (convert written numbers to digits)
- Special character handling
- Code-mixed text normalization
"""

import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class NormalizationService:
    """
    Text normalization and transliteration service
    
    Handles:
    - Cleaning and standardizing text
    - Transliteration between scripts
    - Number normalization
    - Code-mixed text handling
    """
    
    def __init__(self):
        """Initialize normalization service"""
        logger.info("Normalization Service initialized")
        
        self.transliteration_map = self._build_transliteration_map()
    
    def _build_transliteration_map(self) -> Dict[str, str]:
        """Build basic transliteration mappings"""
        return {
            'hai': 'है',
            'main': 'में',
            'ke': 'के',
            'ki': 'की',
            'ka': 'का',
            'ko': 'को',
            'se': 'से',
            'mein': 'में',
            'hain': 'हैं',
            'nahi': 'नहीं',
            'nahin': 'नहीं',
        }
    
    def normalize(self, text: str, language: Optional[str] = None) -> Dict[str, any]:
        """
        Normalize text - main entry point
        
        Args:
            text: Input text to normalize
            language: Optional language hint (for transliteration)
        
        Returns:
            Dictionary with:
            - normalized_text: Cleaned and normalized text
            - original_text: Original input
            - changes_made: List of changes applied
        """
        original = text
        changes = []
        
        cleaned = self._clean_text(text)
        if cleaned != text:
            changes.append("cleaned_whitespace")
        
        normalized = self._normalize_numbers(cleaned)
        if normalized != cleaned:
            changes.append("normalized_numbers")
        
        normalized = self._normalize_currency(normalized)
        if normalized != cleaned:
            changes.append("normalized_currency")
        
        
        if language and language.lower() in ['hindi', 'hi']:
            transliterated = self._transliterate_to_devanagari(normalized)
            if transliterated != normalized:
                changes.append("transliterated_to_devanagari")
                normalized = transliterated
        
        return {
            'normalized_text': normalized,
            'original_text': original,
            'changes_made': changes,
            'confidence': 1.0 if not changes else 0.95
        }
    
    def _clean_text(self, text: str) -> str:
        """
        Basic text cleaning
        
        - Remove extra whitespace
        - Normalize line breaks
        - Trim leading/trailing spaces
        """
        text = re.sub(r'\s+', ' ', text)
        
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\r+', ' ', text)
        
        text = text.strip()
        
        return text
    
    def _normalize_numbers(self, text: str) -> str:
        """
        Normalize written numbers to digits (conservative approach)
        
        Only handles simple cases. Complex cases like "fifty thousand" 
        are better handled by NLU extraction.
        """
        simple_numbers = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90'
        }
        
        for word, num in simple_numbers.items():
            pattern = r'\b' + re.escape(word) + r'\b(?!\s+(?:thousand|lakh|crore|hundred))'
            text = re.sub(pattern, num, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_currency(self, text: str) -> str:
        """
        Normalize currency representations
        
        Examples:
        - "Rs. 50000" -> "₹50000"
        - "rupees 50000" -> "₹50000"
        - "50000 rs" -> "₹50000"
        """
        patterns = [
            (r'\bRs\.\s*', '₹'),  # "Rs. " or "Rs." (word boundary + requires dot)
            (r'\bRs\s+', '₹'),  # "Rs " (word boundary + space, ensures not "years")
            (r'\brupees?\s+', '₹'),  # "rupee " or "rupees " (word boundary ensures standalone)
            (r'(?<!\w)rs\.(?!\w)', '₹'),  # "rs." NOT part of a word (requires dot)
            (r'(?<!\w)\s+rs\b', '₹'),  # " rs" at end of word (space before, word boundary after)
            (r'\bINR\s+', '₹'),  # "INR " (word boundary)
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _transliterate_to_devanagari(self, text: str) -> str:
        """
        Basic transliteration from Roman/Hinglish to Devanagari
        
        Note: This is a simplified version. For production, use:
        - indic-transliteration library
        - or Google's transliteration API
        
        This handles common loan-related terms.
        """
        
        words = text.split()
        transliterated_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower in self.transliteration_map:
                transliterated_words.append(self.transliteration_map[word_lower])
            else:
                transliterated_words.append(word)
        
        return ' '.join(transliterated_words)
    
    def _remove_special_chars(self, text: str, keep_currency: bool = True) -> str:
        """
        Remove special characters (optional)
        
        Args:
            text: Input text
            keep_currency: Keep currency symbols like ₹
        """
        if keep_currency:
            pattern = r'[^\w\s₹.,!?]'
        else:
            pattern = r'[^\w\s]'
        
        return re.sub(pattern, '', text)
    
    def normalize_for_nlu(self, text: str) -> str:
        """
        Normalize text specifically for NLU processing
        
        This ensures text is in the best format for extraction
        """
        result = self.normalize(text)
        return result['normalized_text']



if __name__ == "__main__":
    print("=" * 60)
    print("Text Normalization Service Test")
    print("=" * 60)
    
    service = NormalizationService()
    
    test_cases = [
        "I need  Rs. 50000  loan",
        "मुझे 5 लाख चाहिए",
        "My income is fifty thousand",
        "I need 5 lakh rupees",
        "Rs.50000",
    ]
    
    print("\nTesting normalization:")
    for test in test_cases:
        result = service.normalize(test)
        print(f"\nOriginal:  '{test}'")
        print(f"Normalized: '{result['normalized_text']}'")
        print(f"Changes:   {result['changes_made']}")
    
    print("\n" + "=" * 60)
    print("✅ Normalization Service ready!")
    print("=" * 60)

