#!/usr/bin/env python3
"""
Video Transcript Extractor

Extracts audio from video files and generates transcripts using DashScope ASR.
Creates .txt files with the same name as the video files.

Usage:
    python extract_transcripts.py                    # Process all videos in videos/
    python extract_transcripts.py video1.mp4         # Process specific video
    python extract_transcripts.py --force            # Overwrite existing transcripts
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv
import dashscope
from dashscope.audio.asr import Recognition

# Load environment variables
load_dotenv()

# Configuration
VIDEOS_DIR = 'videos'
TEMP_AUDIO_DIR = 'temp_audio'
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv']


def check_ffmpeg():
    """Check if ffmpeg is installed"""
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True,
                              text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def extract_audio(video_path, audio_path):
    """
    Extract audio from video file using ffmpeg

    Args:
        video_path: Path to video file
        audio_path: Path to save audio file

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"  📹 Extracting audio from {os.path.basename(video_path)}...")

    # ffmpeg command to extract audio as WAV (16kHz, mono, 16-bit)
    cmd = [
        'ffmpeg',
        '-i', video_path,           # Input video
        '-vn',                      # No video
        '-acodec', 'pcm_s16le',     # PCM 16-bit little-endian
        '-ar', '16000',             # 16kHz sample rate
        '-ac', '1',                 # Mono
        '-y',                       # Overwrite output file
        audio_path
    ]

    try:
        result = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              timeout=300)  # 5 minute timeout

        if result.returncode == 0:
            file_size = os.path.getsize(audio_path)
            print(f"  ✅ Audio extracted: {file_size / 1024 / 1024:.2f} MB")
            return True
        else:
            print(f"  ❌ ffmpeg error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ❌ Timeout: Video too long (>5 minutes)")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def transcribe_audio(audio_path):
    """
    Transcribe audio file using DashScope ASR

    Args:
        audio_path: Path to audio file (WAV format)

    Returns:
        str: Transcript text, or None if failed
    """
    print(f"  🎤 Transcribing audio...")

    try:
        # Create recognition instance (synchronous mode)
        recognition = Recognition(
            model='paraformer-realtime-v2',
            format='wav',
            sample_rate=16000,
            callback=None  # Synchronous mode
        )

        # Call recognition
        result = recognition.call(audio_path)

        # Check result
        if isinstance(result, dict) and result.get('status_code') == 200:
            # Extract transcript
            transcript = extract_transcript_from_result(result)

            if transcript:
                print(f"  ✅ Transcription complete: {len(transcript)} characters")
                return transcript
            else:
                print(f"  ⚠️  No transcript found in result")
                return None
        else:
            error_msg = result.get('message', 'Unknown error') if isinstance(result, dict) else str(result)
            print(f"  ❌ DashScope error: {error_msg}")
            return None

    except Exception as e:
        print(f"  ❌ Transcription error: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_transcript_from_result(result):
    """Extract transcript text from DashScope result"""
    if not result:
        return ''

    try:
        # Handle RecognitionResult object
        if hasattr(result, 'output'):
            output = result.output
        elif isinstance(result, dict):
            output = result.get('output')
        else:
            return ''

        if not output:
            return ''

        # Try different output formats
        if isinstance(output, dict):
            # Method 1: output.sentence array (most common for file-based recognition)
            if 'sentence' in output:
                sentences = output['sentence']
                if isinstance(sentences, list):
                    texts = []
                    for sentence in sentences:
                        if isinstance(sentence, dict) and 'text' in sentence:
                            texts.append(sentence['text'])
                    if texts:
                        return ''.join(texts)

            # Method 2: output.text
            if 'text' in output and output['text']:
                return output['text']

            # Method 3: output.sentence.text (single sentence)
            if 'sentence' in output:
                sentence = output['sentence']
                if isinstance(sentence, dict) and 'text' in sentence:
                    return sentence['text']

            # Method 4: output.results array
            if 'results' in output:
                results = output['results']
                if isinstance(results, list):
                    texts = []
                    for r in results:
                        if isinstance(r, dict):
                            text = r.get('text') or r.get('transcription_text', '')
                            if text:
                                texts.append(text)
                    if texts:
                        return ''.join(texts)

        # Method 5: output is string
        if isinstance(output, str):
            return output

    except Exception as e:
        print(f"  ⚠️  Error extracting transcript: {e}")
        import traceback
        traceback.print_exc()

    return ''


def save_transcript(video_path, transcript):
    """
    Save transcript to .txt file

    Args:
        video_path: Path to video file
        transcript: Transcript text

    Returns:
        str: Path to saved transcript file
    """
    # Create .txt filename
    txt_path = Path(video_path).with_suffix('.txt')

    # Save transcript
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(transcript)

    print(f"  💾 Saved transcript to: {txt_path}")
    return str(txt_path)


def process_video(video_path, force=False):
    """
    Process a single video file

    Args:
        video_path: Path to video file
        force: If True, overwrite existing transcript

    Returns:
        bool: True if successful, False otherwise
    """
    video_path = Path(video_path)

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False

    # Check if transcript already exists
    txt_path = video_path.with_suffix('.txt')
    if txt_path.exists() and not force:
        print(f"⏭️  Skipping {video_path.name} (transcript already exists)")
        print(f"   Use --force to overwrite")
        return True

    print(f"\n{'='*60}")
    print(f"Processing: {video_path.name}")
    print(f"{'='*60}")

    # Create temp audio directory
    os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

    # Extract audio
    audio_path = os.path.join(TEMP_AUDIO_DIR, f"{video_path.stem}.wav")

    if not extract_audio(str(video_path), audio_path):
        return False

    try:
        # Transcribe audio
        transcript = transcribe_audio(audio_path)

        if not transcript:
            print(f"  ❌ Failed to get transcript")
            return False

        # Save transcript
        save_transcript(str(video_path), transcript)

        print(f"  ✅ Success!")
        return True

    finally:
        # Clean up temp audio file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"  🗑️  Cleaned up temp audio file")


def main():
    parser = argparse.ArgumentParser(
        description='Extract transcripts from video files using DashScope ASR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_transcripts.py                    # Process all videos
  python extract_transcripts.py video1.mp4         # Process specific video
  python extract_transcripts.py --force            # Overwrite existing transcripts
  python extract_transcripts.py video1.mp4 --force # Force process specific video
        """
    )

    parser.add_argument('videos', nargs='*',
                       help='Specific video files to process (optional)')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Overwrite existing transcript files')
    parser.add_argument('--dir', default=VIDEOS_DIR,
                       help=f'Video directory (default: {VIDEOS_DIR})')

    args = parser.parse_args()

    print("=" * 60)
    print("Video Transcript Extractor")
    print("=" * 60)

    # Check ffmpeg
    if not check_ffmpeg():
        print("\n❌ Error: ffmpeg is not installed")
        print("\nPlease install ffmpeg:")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt-get install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        return 1

    print("✅ ffmpeg is installed")

    # Check DashScope API key
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print("\n❌ Error: DASHSCOPE_API_KEY not configured")
        print("\nPlease set your API key in .env file:")
        print("  DASHSCOPE_API_KEY=sk-your-key-here")
        return 1

    dashscope.api_key = api_key
    print(f"✅ DashScope API key configured: {api_key[:10]}...")

    # Get list of videos to process
    if args.videos:
        # Process specific videos
        video_files = [Path(v) for v in args.videos]
    else:
        # Process all videos in directory
        video_dir = Path(args.dir)
        if not video_dir.exists():
            print(f"\n❌ Error: Video directory not found: {video_dir}")
            return 1

        video_files = []
        for ext in SUPPORTED_VIDEO_FORMATS:
            video_files.extend(video_dir.glob(f"*{ext}"))

        if not video_files:
            print(f"\n⚠️  No video files found in {video_dir}")
            return 0

    print(f"\n📹 Found {len(video_files)} video(s) to process")

    # Process videos
    success_count = 0
    fail_count = 0
    skip_count = 0

    for video_file in video_files:
        # Check if transcript exists before processing
        txt_path = video_file.with_suffix('.txt')
        existed_before = txt_path.exists()

        result = process_video(video_file, force=args.force)

        if result:
            # Check if it was actually processed or skipped
            if existed_before and not args.force:
                skip_count += 1
            else:
                success_count += 1
        else:
            fail_count += 1

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"✅ Successful: {success_count}")
    print(f"⏭️  Skipped:    {skip_count}")
    print(f"❌ Failed:     {fail_count}")
    print(f"📊 Total:      {len(video_files)}")

    if success_count > 0:
        print(f"\n💡 Tip: Restart the server to load the new transcripts")
        print(f"   python server.py")

    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
