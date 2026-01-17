#!/usr/bin/env python3
"""
Video Compression Script for Mobile Devices

Compresses videos to optimize for mobile playback with reduced file sizes
while maintaining acceptable quality.

Usage:
    python compress_videos.py                           # Balanced compression
    python compress_videos.py --quality high            # High quality
    python compress_videos.py --quality maximum         # Maximum compression
    python compress_videos.py --input my_videos --output compressed
"""

import os
import subprocess
import sys
from pathlib import Path
import argparse


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def compress_video(input_path, output_path, quality='balanced', verbose=True):
    """
    Compress video for mobile devices.

    Args:
        input_path: Path to input video
        output_path: Path to output video
        quality: 'high', 'balanced', or 'maximum'
        verbose: Print progress information

    Returns:
        True if successful, False otherwise
    """

    # Quality presets
    presets = {
        'high': {
            'scale': '1280:-2',
            'crf': '23',
            'audio_bitrate': '128k',
            'description': 'High quality (1280px, ~60-70% reduction)'
        },
        'balanced': {
            'scale': '720:-2',
            'crf': '28',
            'audio_bitrate': '96k',
            'description': 'Balanced (720px, ~50-60% reduction)'
        },
        'maximum': {
            'scale': '480:-2',
            'crf': '32',
            'audio_bitrate': '64k',
            'description': 'Maximum compression (480px, ~70-80% reduction)'
        }
    }

    preset = presets.get(quality, presets['balanced'])

    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-vf', f"scale={preset['scale']}",
        '-c:v', 'libx264',
        '-crf', preset['crf'],
        '-preset', 'medium',
        '-c:a', 'aac',
        '-b:a', preset['audio_bitrate'],
        '-y',  # Overwrite output
        str(output_path)
    ]

    if verbose:
        print(f"📹 Compressing: {Path(input_path).name}")
        print(f"   Quality: {preset['description']}")

    try:
        # Run ffmpeg with suppressed output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Show file size comparison
        original_size = os.path.getsize(input_path) / (1024 * 1024)
        compressed_size = os.path.getsize(output_path) / (1024 * 1024)
        reduction = (1 - compressed_size / original_size) * 100

        if verbose:
            print(f"   ✅ Original:    {original_size:.2f} MB")
            print(f"   ✅ Compressed:  {compressed_size:.2f} MB")
            print(f"   ✅ Reduction:   {reduction:.1f}%")
            print()

        return True

    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"   ❌ Error: {e}")
            if e.stderr:
                print(f"   Details: {e.stderr[:200]}")
            print()
        return False


def compress_directory(input_dir='videos', output_dir='videos_mobile', quality='balanced'):
    """
    Compress all videos in a directory.

    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        quality: Compression quality level

    Returns:
        Tuple of (success_count, failed_count)
    """

    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Check if input directory exists
    if not input_path.exists():
        print(f"❌ Error: Input directory '{input_dir}' does not exist")
        return 0, 0

    # Create output directory
    output_path.mkdir(exist_ok=True)

    # Find all video files
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    videos = []
    for ext in video_extensions:
        videos.extend(input_path.glob(f'*{ext}'))

    if not videos:
        print(f"❌ No videos found in '{input_dir}'")
        print(f"   Looking for: {', '.join(video_extensions)}")
        return 0, 0

    print("=" * 60)
    print("Video Compression for Mobile Devices")
    print("=" * 60)
    print(f"📁 Input:  {input_dir}")
    print(f"📁 Output: {output_dir}")
    print(f"🎯 Quality: {quality}")
    print(f"📹 Videos: {len(videos)}")
    print("=" * 60)
    print()

    success_count = 0
    failed_count = 0

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] ", end="")

        try:
            output_file = output_path / video.name
            if compress_video(str(video), str(output_file), quality):
                success_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ Unexpected error: {e}\n")
            failed_count += 1

    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed:     {failed_count}")
    print(f"📊 Total:      {len(videos)}")
    print("=" * 60)

    if success_count > 0:
        print()
        print("💡 Next steps:")
        print(f"   1. Test compressed videos: ffplay {output_dir}/<video>.mp4")
        print(f"   2. Replace original videos if satisfied")
        print(f"   3. Restart server: python server.py")

    return success_count, failed_count


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description='Compress videos for mobile devices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python compress_videos.py                           # Balanced compression
  python compress_videos.py --quality high            # High quality
  python compress_videos.py --quality maximum         # Maximum compression
  python compress_videos.py --input my_videos --output compressed

Quality levels:
  high     - 1280px width, CRF 23, 128k audio (~60-70% reduction)
  balanced - 720px width, CRF 28, 96k audio (~50-60% reduction) [DEFAULT]
  maximum  - 480px width, CRF 32, 64k audio (~70-80% reduction)
        """
    )

    parser.add_argument(
        '--input',
        default='videos',
        help='Input directory (default: videos)'
    )

    parser.add_argument(
        '--output',
        default='videos_mobile',
        help='Output directory (default: videos_mobile)'
    )

    parser.add_argument(
        '--quality',
        choices=['high', 'balanced', 'maximum'],
        default='balanced',
        help='Compression quality (default: balanced)'
    )

    args = parser.parse_args()

    # Check ffmpeg
    if not check_ffmpeg():
        print("❌ Error: ffmpeg is not installed")
        print()
        print("Please install ffmpeg:")
        print("  macOS:   brew install ffmpeg")
        print("  Ubuntu:  sudo apt-get install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        sys.exit(1)

    # Compress videos
    success, failed = compress_directory(args.input, args.output, args.quality)

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
