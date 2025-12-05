"""
Interactive STT Test

Test STT service interactively - you can provide an audio file or test initialization.
"""

import sys
import os
from stt_service import STTService

def main():
    print("=" * 60)
    print("🎤 Interactive STT Service Test")
    print("=" * 60)
    
    # Test initialization
    print("\n1. Testing STT Service Initialization...")
    try:
        stt = STTService(model_name='tiny')
        print("   ✓ STT Service initialized!")
        print(f"   Model: {stt.model_name}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Check if audio file provided
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        print(f"\n2. Testing with audio file: {audio_file}")
        
        if not os.path.exists(audio_file):
            print(f"   ❌ File not found: {audio_file}")
            return
        
        try:
            print("   Transcribing... (this may take a moment)")
            result = stt.transcribe_file(audio_file)
            
            print("\n   ✓ Transcription successful!")
            print(f"\n   📝 Transcribed Text:")
            print(f"   '{result['text']}'")
            print(f"\n   📊 Details:")
            print(f"   Language: {result['language']}")
            print(f"   Confidence: {result['confidence']:.1%}")
            print(f"   Segments: {result['segments']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("\n2. No audio file provided")
        print("\n   To test with an audio file:")
        print(f"   python3 test_stt_interactive.py <audio_file>")
        print("\n   Example:")
        print(f"   python3 test_stt_interactive.py test_audio.mp3")
        print("\n   Supported formats: mp3, wav, m4a, flac, ogg, etc.")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

