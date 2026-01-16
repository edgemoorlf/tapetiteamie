# Extract Transcripts Script - Quick Guide

## Prerequisites

### 1. Install ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### 2. Configure DashScope API Key

Make sure `.env` file has your API key:
```
DASHSCOPE_API_KEY=sk-your-key-here
```

## Usage

### Process All Videos

```bash
python extract_transcripts.py
```

This will:
- Find all `.mp4`, `.avi`, `.mov`, `.mkv` files in `videos/` directory
- Extract audio from each video
- Transcribe using DashScope ASR
- Save transcripts as `.txt` files
- Skip videos that already have transcripts

### Process Specific Video

```bash
python extract_transcripts.py videos/introduction.mp4
```

### Overwrite Existing Transcripts

```bash
python extract_transcripts.py --force
```

### Process Specific Video with Force

```bash
python extract_transcripts.py videos/introduction.mp4 --force
```

### Use Different Directory

```bash
python extract_transcripts.py --dir /path/to/videos
```

## Example Output

```
============================================================
Video Transcript Extractor
============================================================
✅ ffmpeg is installed
✅ DashScope API key configured: sk-89daa2f...

📹 Found 3 video(s) to process

============================================================
Processing: introduction.mp4
============================================================
  📹 Extracting audio from introduction.mp4...
  ✅ Audio extracted: 2.34 MB
  🎤 Transcribing audio...
  ✅ Transcription complete: 156 characters
  💾 Saved transcript to: videos/introduction.txt
  🗑️  Cleaned up temp audio file
  ✅ Success!

============================================================
Processing: tutorial.mp4
============================================================
  📹 Extracting audio from tutorial.mp4...
  ✅ Audio extracted: 5.67 MB
  🎤 Transcribing audio...
  ✅ Transcription complete: 342 characters
  💾 Saved transcript to: videos/tutorial.txt
  🗑️  Cleaned up temp audio file
  ✅ Success!

⏭️  Skipping demo.mp4 (transcript already exists)
   Use --force to overwrite

============================================================
Summary
============================================================
✅ Successful: 2
⏭️  Skipped:    1
❌ Failed:     0
📊 Total:      3

💡 Tip: Restart the server to load the new transcripts
   python server.py
```

## What It Does

1. **Extracts Audio**
   - Uses ffmpeg to extract audio from video
   - Converts to WAV format (16kHz, mono, 16-bit PCM)
   - Saves to `temp_audio/` directory temporarily

2. **Transcribes Audio**
   - Sends audio to DashScope ASR API
   - Uses `paraformer-realtime-v2` model
   - Synchronous mode (waits for complete result)

3. **Saves Transcript**
   - Creates `.txt` file with same name as video
   - Saves in same directory as video
   - UTF-8 encoding

4. **Cleans Up**
   - Deletes temporary audio file
   - Keeps only the transcript

## File Structure

**Before:**
```
videos/
  ├── introduction.mp4
  ├── tutorial.mp4
  └── demo.mp4
```

**After:**
```
videos/
  ├── introduction.mp4
  ├── introduction.txt    ← NEW
  ├── tutorial.mp4
  ├── tutorial.txt        ← NEW
  ├── demo.mp4
  └── demo.txt            ← NEW
```

## Troubleshooting

### Error: ffmpeg not installed

```
❌ Error: ffmpeg is not installed

Please install ffmpeg:
  macOS:   brew install ffmpeg
  Ubuntu:  sudo apt-get install ffmpeg
  Windows: Download from https://ffmpeg.org/download.html
```

**Solution:** Install ffmpeg using the command for your OS.

### Error: DASHSCOPE_API_KEY not configured

```
❌ Error: DASHSCOPE_API_KEY not configured

Please set your API key in .env file:
  DASHSCOPE_API_KEY=sk-your-key-here
```

**Solution:** Add your API key to `.env` file.

### Error: Video not found

```
❌ Video not found: videos/intro.mp4
```

**Solution:** Check the file path and name are correct.

### Error: ffmpeg timeout

```
❌ Timeout: Video too long (>5 minutes)
```

**Solution:** The script has a 5-minute timeout per video. For longer videos, you may need to split them or increase the timeout in the script.

### Error: DashScope API error

```
❌ DashScope error: NO_VALID_AUDIO_ERROR
```

**Solution:**
- Check video has audio track
- Check audio is not corrupted
- Try with a different video

### Warning: No transcript found

```
⚠️  No transcript found in result
```

**Solution:**
- Video may have no speech
- Audio quality may be too poor
- Try with a video that has clear speech

## Tips

### 1. Batch Processing

Process all videos at once:
```bash
python extract_transcripts.py
```

Then go get coffee while it processes! ☕

### 2. Check Before Overwriting

The script skips existing transcripts by default. This is useful if you:
- Add new videos to the directory
- Want to re-run without re-processing everything

### 3. Manual Review

After extraction, review the transcripts:
```bash
cat videos/introduction.txt
```

Edit if needed to improve accuracy.

### 4. Restart Server

After creating transcripts, restart the server to load them:
```bash
python server.py
```

Check server logs for:
```
INFO:__main__:Loaded transcript for introduction.mp4: 156 chars
```

## Performance

**Typical processing time:**
- 1 minute video: ~30-60 seconds
- 5 minute video: ~2-5 minutes
- 10 minute video: ~5-10 minutes

**Factors affecting speed:**
- Video length
- Audio quality
- Network speed (DashScope API)
- CPU speed (ffmpeg extraction)

## Cost

**DashScope ASR pricing:**
- Check current pricing at: https://dashscope.console.aliyun.com/
- Typically charged per minute of audio
- Free tier may be available

**Estimate:**
- 10 videos × 2 minutes each = 20 minutes of audio
- Check DashScope pricing for exact cost

## Advanced Usage

### Custom Video Directory

```bash
python extract_transcripts.py --dir /path/to/my/videos
```

### Process Multiple Specific Videos

```bash
python extract_transcripts.py video1.mp4 video2.mp4 video3.mp4
```

### Force Overwrite All

```bash
python extract_transcripts.py --force
```

Useful when:
- You want to re-transcribe with better audio
- Previous transcription had errors
- You updated the video content

## Summary

✅ **Automated transcript extraction**
✅ **Supports multiple video formats**
✅ **Uses DashScope ASR for accuracy**
✅ **Handles sentence array format** (output.sentence[])
✅ **Automatic cleanup**
✅ **Skip existing transcripts**
✅ **Batch processing**
✅ **Clear progress indicators**

Just run `python extract_transcripts.py` and let it do the work!

## Verified Working

The script has been tested and verified to work with:
- ✅ introduction.mp4 - "虚里同学，我一直对你很有好感。"
- ✅ All 9 videos in the videos/ directory
- ✅ Correctly extracts Chinese speech
- ✅ Handles DashScope's sentence array format
