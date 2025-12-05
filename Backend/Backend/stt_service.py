"""
Speech-to-Text (STT) Service

This module handles converting audio input to text using LOCAL Whisper model.

Features:
- Runs locally (no API key needed)
- Supports multiple audio formats
- Handles different languages (Hindi, English, Tamil, etc.)
- Code-mixed speech support
- Error handling and retries
"""

import os
import logging
from typing import Optional
from pathlib import Path
import tempfile
import ssl
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not installed. Install with: pip install openai-whisper")
DEFAULT_WHISPER_MODEL = "base"


class STTService:
    """
    Speech-to-Text service using local Whisper model
    
    Supports:
    - Multiple languages (auto-detect or specify)
    - Code-mixed speech (Hindi-English, etc.)
    - Various audio formats (mp3, wav, m4a, etc.)
    - Runs locally (no API key needed)
    """
    
    def __init__(self, model_name: str = DEFAULT_WHISPER_MODEL):
        """
        Initialize STT service with local Whisper model
        
        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
                       Default: "base" (good balance of speed and accuracy)
        
        Raises:
            ImportError: If whisper package is not installed
        """
        if not WHISPER_AVAILABLE:
            raise ImportError(
                "Whisper not installed! Please install it:\n"
                "  pip install openai-whisper\n"
                "Note: You may also need: pip install ffmpeg-python"
            )
        
        self.model_name = model_name
        self.model = None
        
        logger.info(f"Loading Whisper model: {model_name} (this may take a moment on first run)...")
        try:
            self.model = whisper.load_model(model_name)
            logger.info(f"✓ Whisper model '{model_name}' loaded successfully")
        except Exception as e:
            error_msg = str(e)
            raise Exception(
                f"Failed to load Whisper model: {e}\n\n"
                f"Possible solutions:\n"
                f"1. Check your internet connection\n"
                f"2. If behind a proxy/firewall, configure network settings\n"
                f"3. Install Python certificates: /Applications/Python\\ 3.13/Install\\ Certificates.command\n"
                f"4. Manually download model and place in ~/.cache/whisper/\n"
                f"5. Try a different model size (tiny, base, small)"
            )
    
    def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio to text using local Whisper model
        
        Args:
            audio_data: Audio file bytes
            language: Optional language code (e.g., "hi", "en", "ta")
                     If None, Whisper will auto-detect
            prompt: Optional prompt to guide transcription
                   (useful for loan-related terms)
        
        Returns:
            Dictionary with:
            - text: Transcribed text
            - language: Detected language
            - confidence: Average probability from Whisper
        """
        if not self.model:
            raise Exception("Whisper model not loaded")
        
        try:
            logger.info(f"Transcribing audio (size: {len(audio_data)} bytes)")

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name
            
            try:
                result = self.model.transcribe(
                    tmp_file_path,
                    language=language,
                    initial_prompt=prompt,
                    verbose=False
                )
                
                transcribed_text = result.get('text', '').strip()
                detected_language = result.get('language', 'unknown')
            
                segments = result.get('segments', [])
                if segments:
                    avg_confidence = sum(seg.get('no_speech_prob', 0.5) for seg in segments) / len(segments)
                    confidence = 1.0 - avg_confidence
                else:
                    confidence = 0.9
                
                logger.info(f"Transcription successful: {len(transcribed_text)} characters, language: {detected_language}")
                
                return {
                    'text': transcribed_text,
                    'language': detected_language,
                    'confidence': confidence,
                    'segments': len(segments)
                }
                
            finally:
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def transcribe_file(
        self,
        file_path: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio from file (direct file path, more efficient)
        
        Args:
            file_path: Path to audio file
            language: Optional language code
            prompt: Optional prompt
        
        Returns:
            Transcription result dictionary
        """
        if not self.model:
            raise Exception("Whisper model not loaded")
        
        try:
            logger.info(f"Transcribing file: {file_path}")
            
            result = self.model.transcribe(
                file_path,
                language=language,
                initial_prompt=prompt,
                verbose=False
            )
            
            transcribed_text = result.get('text', '').strip()
            detected_language = result.get('language', 'unknown')
            
            segments = result.get('segments', [])
            if segments:
                avg_confidence = sum(seg.get('no_speech_prob', 0.5) for seg in segments) / len(segments)
                confidence = 1.0 - avg_confidence
            else:
                confidence = 0.9
            
            logger.info(f"Transcription successful: {len(transcribed_text)} characters, language: {detected_language}")
            
            return {
                'text': transcribed_text,
                'language': detected_language,
                'confidence': confidence,
                'segments': len(segments)
            }
            
        except FileNotFoundError:
            raise Exception(f"Audio file not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error transcribing audio file: {str(e)}")
    
    def transcribe_with_fallback(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        max_retries: int = 3
    ) -> dict:
        """
        Transcribe with retry logic and fallback
        
        Args:
            audio_data: Audio file bytes
            language: Optional language code
            max_retries: Maximum retry attempts
        
        Returns:
            Transcription result or error message
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                prompt = "This is a conversation about loan eligibility, EMI, interest rates, and financial information."
                return self.transcribe(audio_data, language, prompt)
            except Exception as e:
                last_error = e
                logger.warning(f"Transcription attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(1)
        
        logger.error(f"All transcription attempts failed: {last_error}")
        return {
            'text': '',
            'language': 'unknown',
            'confidence': 0.0,
            'error': str(last_error)
        }


SUPPORTED_LANGUAGES = {
    'hindi': 'hi',
    'english': 'en',
    'tamil': 'ta',
    'telugu': 'te',
    'kannada': 'kn',
    'malayalam': 'ml',
    'bengali': 'bn',
    'gujarati': 'gu',
    'marathi': 'mr',
    'punjabi': 'pa',
    'urdu': 'ur'
}


def get_language_code(language_name: str) -> Optional[str]:
    """Convert language name to Whisper language code"""
    return SUPPORTED_LANGUAGES.get(language_name.lower())

if __name__ == "__main__":
    print("=" * 60)
    print("STT Service (Local Whisper)")
    print("=" * 60)
    print("\nThis service uses LOCAL Whisper model (no API key needed)")
    print("\nRequirements:")
    print("1. Install: pip install openai-whisper")
    print("2. Optional: pip install ffmpeg-python (for better audio support)")
    print("3. Audio file to transcribe")
    print("\nTo test:")
    print("  python3 -c \"from stt_service import STTService; stt = STTService(); print('✓ STT Service ready!')\"")
    print("\nNote: First run will download the model (one-time, ~150MB for 'base' model)")
    print("=" * 60)
