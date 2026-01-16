# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a voice-interactive video player application that allows users to control video playback through voice commands. The system uses Alibaba Cloud's DashScope API for real-time speech recognition (ASR) with streaming audio and consists of a Flask backend server with WebSocket support and a vanilla JavaScript frontend.

**Key Feature**: Real-time streaming speech recognition - audio is continuously captured and sent to DashScope as PCM blocks, with partial transcription results displayed in real-time.

## Architecture

### Backend (server.py)
- **Flask server** with **flask-socketio** for WebSocket support, running on port 5001
- **DashScope ASR integration** using the `paraformer-realtime-v2` model with streaming
- **Real-time audio processing**: Receives PCM blocks via WebSocket and streams to DashScope
- **StreamingRecognitionCallback**: Custom callback handler for processing recognition events
- **Session management**: Thread-safe tracking of active recognition sessions
- **Video management**: Serves videos from the `videos/` directory

### Frontend (public/index.html)
- **Single-page application** with vanilla JavaScript and Socket.IO client
- **AudioContext API** for real-time PCM audio conversion (16kHz, mono)
- **ScriptProcessorNode**: Captures audio in 4096-sample buffers (~256ms)
- **WebSocket streaming**: Continuously sends PCM blocks to server
- **Real-time feedback**: Displays partial transcription results as they arrive
- **Video preloading**: Automatically preloads next 2 videos for smooth transitions
- **Voice matching logic**: Supports Chinese number expressions ("第一个", "视频1", "1")

### Key Flow (Streaming)
1. Video plays to completion
2. Voice prompt appears automatically
3. User speaks for 5 seconds (audio captured continuously)
4. Browser converts audio to PCM and streams via WebSocket
5. Server feeds PCM blocks to DashScope Recognition in real-time
6. Partial transcription results sent back to client
7. Final transcript matched against video names
8. Matching video loads and plays automatically

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your DASHSCOPE_API_KEY
```

### Running the Application
```bash
# Start the server (runs on http://localhost:5001)
python server.py
```

### Testing
```bash
# Test DashScope API configuration
python test_dashscope.py

# Test audio file recognition
python test_audio.py <path-to-audio-file>
# Example: python test_audio.py temp_audio/recording.webm

# Extract transcripts from videos (requires ffmpeg)
python extract_transcripts.py
# Or for specific video:
python extract_transcripts.py videos/intro.mp4
```

## Configuration

### Environment Variables (.env)
- `DASHSCOPE_API_KEY`: Required. Get from https://dashscope.console.aliyun.com/apiKey

### Directory Structure
- `videos/`: Place MP4 video files here (automatically served)
  - Videos are sorted with `introduction.mp4` first, then alphabetically
  - Add matching `.txt` files for transcript-based matching
- `temp_audio/`: Temporary storage for audio processing (auto-cleaned)
- `public/`: Frontend static files (index.html)

## DashScope ASR Integration

### Streaming Model Configuration
- **Model**: `paraformer-realtime-v2` (real-time speech recognition)
- **Format**: PCM (16-bit signed integer)
- **Sample Rate**: 16000 Hz
- **Channels**: Mono (1 channel)
- **Language**: Chinese (Mandarin)
- **Streaming API**: `start()` → `send_audio_frame(bytes)` → `stop()`

### Callback Implementation
The `StreamingRecognitionCallback` class handles recognition events:
- `on_open()`: Connection established, emit to client
- `on_event(result)`: Partial/final results, extract and emit transcript
- `on_complete()`: Recognition finished, emit final result
- `on_error(result)`: Error occurred, emit error to client
- `on_close()`: Connection closed, cleanup

### WebSocket Events
**Client → Server:**
- `start_recognition`: Initialize recognition session
- `audio_data`: Send PCM audio blocks (as byte arrays)
- `stop_recognition`: End recognition session

**Server → Client:**
- `recognition_started`: Session initialized
- `recognition_result`: Partial transcription (real-time)
- `recognition_complete`: Final transcription
- `recognition_error`: Error occurred
- `recognition_closed`: Session closed

### Response Parsing
The `_extract_transcript()` method handles multiple DashScope response formats:
- `result.response.output.text` (most common)
- `result.response.output.sentence.text`
- Direct string output

### Error Handling
- API key validation on startup
- Session cleanup on disconnect
- Thread-safe session management with Lock
- Graceful fallback: plays next video if recognition fails
- Detailed logging for debugging ASR issues

## Important Notes

- WebSocket connections are managed per-client with automatic cleanup on disconnect
- Audio is processed in real-time with ~256ms latency (4096 samples at 16kHz)
- The frontend uses ScriptProcessorNode (deprecated but widely supported) for audio processing
- Session management is thread-safe using Python's threading.Lock
- The old file-based `/api/speech-to-text` endpoint is still available for backward compatibility
- Real-time transcription feedback improves user experience during recognition
- Video matching is case-insensitive and supports multiple Chinese number formats
- The frontend automatically triggers voice recognition when videos end

## Development Progress

See `VOICE.md` for detailed implementation progress and design decisions for the streaming voice recognition feature.

See `VIDEO_MATCHING_REFACTORED.md` for the new modular video matching architecture.

See `LLM_MATCHING.md` for the LLM-based conversational video matching system.

See `TRANSCRIPT_SETUP.md` for guide on adding video transcripts for content-based matching.
