# Video Transcript Setup Guide

## Quick Start

### 1. Create Transcript Files

For each video in `videos/` directory, create a matching `.txt` file:

```
videos/
  ├── introduction.mp4   ← Always shown first
  ├── introduction.txt   ← Create this
  ├── demo.mp4           ← Then alphabetically
  ├── demo.txt           ← Create this
  ├── tutorial.mp4
  └── tutorial.txt       ← Create this
```

**Note:** Videos are automatically sorted with `introduction.mp4` first, then alphabetically by filename.

### 2. Transcript File Format

**File name:** Same as video, but with `.txt` extension
**Encoding:** UTF-8
**Content:** Plain text of what is spoken in the video

**Example: `intro.txt`**
```
大家好，欢迎来到我的频道。
今天我要介绍一个新的项目。
这个项目可以通过语音控制视频播放。
```

### 3. Restart Server

```bash
python server.py
```

The server will automatically load transcripts when fetching videos.

### 4. Test

Say words from the beginning of the video transcript, and it should match!

**Example:**
- Video: `intro.mp4`
- Transcript starts with: "大家好，欢迎来到我的频道"
- User says: "大家好欢迎"
- ✅ Matches `intro.mp4` with high confidence!

## How It Works

### Matching Algorithm

The `TranscriptMatchStrategy` (highest priority) checks:

1. **Beginning Match** (first 100 characters)
   - Splits user speech into words
   - Counts how many words appear in video's first 100 chars
   - If >50% match → High confidence match

2. **Full Transcript Match**
   - Checks entire transcript
   - If >60% of words match → Medium confidence match

### Example

**Video transcript:**
```
大家好，欢迎来到我的频道。今天我们要学习如何使用语音控制视频播放。
这是一个非常有趣的功能，让我们开始吧。
```

**User says:** "大家好欢迎频道"

**Matching process:**
```
Words: ["大家好", "欢迎", "频道"]
Beginning (100 chars): "大家好，欢迎来到我的频道。今天我们要学习如何使用语音控制视频播放。"

Matches in beginning:
- "大家好" ✅
- "欢迎" ✅
- "频道" ✅

Result: 3/3 words matched (100% confidence)
→ Match found!
```

## Tips for Creating Good Transcripts

### 1. **Focus on the Beginning**
The first 100 characters are most important:
```
✅ Good: "大家好，欢迎来到Python教程。今天我们学习..."
❌ Bad: "嗯...那个...好的...大家好..."
```

### 2. **Use Clear, Distinct Words**
```
✅ Good: "机器学习入门教程"
❌ Bad: "这个那个教程"
```

### 3. **Include Key Topics**
```
✅ Good: "今天讲解React Hooks的使用方法"
❌ Bad: "今天讲解一个新功能"
```

### 4. **Remove Filler Words**
```
✅ Good: "欢迎来到频道"
❌ Bad: "嗯...欢迎...那个...来到频道"
```

## Extracting Transcripts from Videos

### Option 1: Automated Script (Recommended)

Use the provided `extract_transcripts.py` script to automatically extract transcripts from all videos:

```bash
# Install ffmpeg first (if not already installed)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg

# Process all videos in videos/ directory
python extract_transcripts.py

# Process specific video
python extract_transcripts.py videos/intro.mp4

# Overwrite existing transcripts
python extract_transcripts.py --force
```

**What it does:**
1. Extracts audio from video using ffmpeg
2. Converts to 16kHz mono WAV format
3. Sends to DashScope ASR for transcription
4. Saves transcript as `.txt` file with same name
5. Cleans up temporary audio files

**Example output:**
```
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
```

### Option 2: Manual Transcription
Watch the video and type what is said.

### Option 3: Use Other ASR Services
- Google Cloud Speech-to-Text
- Azure Speech Services
- AWS Transcribe
- OpenAI Whisper

### Option 4: YouTube Auto-Captions
If video is on YouTube, download auto-generated captions.

## Testing Transcripts

### 1. Check Server Logs

When server starts, you should see:
```
INFO:__main__:Loaded transcript for intro.mp4: 156 chars
INFO:__main__:Loaded transcript for tutorial.mp4: 243 chars
```

### 2. Check Browser Console

When matching occurs:
```
[VideoMatcher] ✅ Match found: {
  transcript: "大家好欢迎",
  videoIndex: 0,
  confidence: "100.0%",
  strategy: "Transcript Match",
  reason: "Transcript match: 3/3 words in beginning"
}
```

### 3. Check Transcript Log Panel

In the UI, you'll see:
```
14:23:45 [DashScope] 匹配结果: 视频 #1 (Transcript Match, 置信度: 100.0%)
```

## Troubleshooting

### Transcript Not Loading

**Problem:** Server doesn't log "Loaded transcript"

**Solutions:**
1. Check file name matches exactly (case-sensitive on Linux)
2. Check file encoding is UTF-8
3. Check file is in `videos/` directory
4. Restart server

### Transcript Not Matching

**Problem:** Says words from transcript but doesn't match

**Solutions:**
1. Check if words are in first 100 characters
2. Try saying more words (need >50% match)
3. Check for typos in transcript
4. Check browser console for matching details

### Low Confidence Matches

**Problem:** Matches but with low confidence

**Solutions:**
1. Add more distinctive words to beginning
2. Remove filler words
3. Make transcript more accurate
4. Say more words from the transcript

## Advanced: Programmatic Transcript Generation

### Python Script to Generate Transcripts

```python
import os
from dashscope.audio.asr import Recognition

def transcribe_video(video_path):
    # Extract audio from video
    audio_path = extract_audio(video_path)

    # Use DashScope to transcribe
    recognition = Recognition(
        model='paraformer-realtime-v2',
        format='wav',
        sample_rate=16000,
        callback=None
    )

    result = recognition.call(audio_path)
    transcript = extract_transcript(result)

    # Save transcript
    txt_path = video_path.replace('.mp4', '.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(transcript)

    print(f"Saved transcript to {txt_path}")

# Process all videos
for video in os.listdir('videos/'):
    if video.endswith('.mp4'):
        transcribe_video(f'videos/{video}')
```

## Example Transcripts

### Example 1: Tutorial Video
**File:** `python-tutorial.txt`
```
大家好，欢迎来到Python编程教程。
今天我们要学习如何使用列表和字典。
首先让我们看看列表的基本操作。
列表是Python中最常用的数据结构之一。
```

### Example 2: Introduction Video
**File:** `channel-intro.txt`
```
大家好，我是小明，欢迎来到我的频道。
这个频道主要分享编程技术和项目实战。
如果你喜欢我的内容，请点赞订阅。
```

### Example 3: Demo Video
**File:** `voice-control-demo.txt`
```
这是一个语音控制视频播放的演示。
你可以通过说话来选择想看的视频。
比如说"第二个"或者"教程"。
非常方便，让我们试试看。
```

## Summary

1. ✅ Create `.txt` files with same name as videos
2. ✅ Use UTF-8 encoding
3. ✅ Put important words at the beginning
4. ✅ Remove filler words
5. ✅ Test by saying words from transcript
6. ✅ Check logs for debugging

With transcripts, users can say **what the video is about** instead of just the filename or number!
