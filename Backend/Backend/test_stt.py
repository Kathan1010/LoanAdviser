"""
Test STT Service

This script tests the Speech-to-Text service with local Whisper.
"""

import sys
import os
from stt_service import STTService, get_language_code

def test_initialization():
    """Test 1: Initialize STT service"""
    print("=" * 60)
    print("TEST 1: STT Service Initialization")
    print("=" * 60)
    
    try:
        print("\nInitializing STT service with 'tiny' model...")
        stt = STTService(model_name='tiny')
        print("✓ STT Service initialized successfully!")
        print(f"  Model: {stt.model_name}")
        return stt
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_with_file(stt, audio_file_path: str):
    """Test 2: Transcribe audio file"""
    print("\n" + "=" * 60)
    print("TEST 2: Transcribe Audio File")
    print("=" * 60)
    
    if not os.path.exists(audio_file_path):
        print(f"❌ File not found: {audio_file_path}")
        return None
    
    try:
        print(f"\nTranscribing: {audio_file_path}")
        result = stt.transcribe_file(audio_file_path)
        
        print("\n✓ Transcription successful!")
        print(f"\nTranscribed Text:")
        print(f"  '{result['text']}'")
        print(f"\nDetails:")
        print(f"  Language: {result['language']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Segments: {result['segments']}")
        
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_language_detection():
    """Test 3: Language code conversion"""
    print("\n" + "=" * 60)
    print("TEST 3: Language Code Conversion")
    print("=" * 60)
    
    test_languages = ['hindi', 'english', 'tamil', 'telugu']
    print("\nTesting language code conversion:")
    for lang in test_languages:
        code = get_language_code(lang)
        print(f"  {lang:10} → {code}")


def test_with_bytes(stt, audio_bytes: bytes, language: str = None):
    """Test 4: Transcribe from bytes"""
    print("\n" + "=" * 60)
    print("TEST 4: Transcribe from Bytes")
    print("=" * 60)
    
    try:
        print(f"\nTranscribing {len(audio_bytes)} bytes of audio...")
        result = stt.transcribe(audio_bytes, language=language)
        
        print("\n✓ Transcription successful!")
        print(f"  Text: '{result['text']}'")
        print(f"  Language: {result['language']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        
        return result
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("🎤 STT Service Test Suite")
    print("=" * 60)
    
    # Test 1: Initialization
    stt = test_initialization()
    if not stt:
        print("\n❌ Cannot proceed without STT service")
        return
    
    # Test 3: Language codes
    test_language_detection()
    
    # Test 2: File transcription (if file provided)
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        test_with_file(stt, audio_file)
    else:
        print("\n" + "=" * 60)
        print("TEST 2: File Transcription (Skipped)")
        print("=" * 60)
        print("\nTo test with an audio file, run:")
        print(f"  python3 test_stt.py <path_to_audio_file>")
        print("\nSupported formats: mp3, wav, m4a, flac, etc.")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\nSTT Service is ready to use in the orchestrator!")
    print("=" * 60)


if __name__ == "__main__":
    main()
