"""
HTTPS-enabled version of the server for production deployment.

Usage:
1. Generate self-signed certificate (for testing):
   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

2. Or use Let's Encrypt certificates (for production):
   sudo certbot certonly --standalone -d yourdomain.com
   # Certificates will be in /etc/letsencrypt/live/yourdomain.com/

3. Run the server:
   python server_https.py
"""

import os
import json
import struct
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback
from dashscope import Generation
from dotenv import load_dotenv
import tempfile
import logging
from threading import Lock
import ssl

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configuration
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')
dashscope.api_key = DASHSCOPE_API_KEY

UPLOAD_FOLDER = 'videos'
TEMP_AUDIO_FOLDER = 'temp_audio'
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
ALLOWED_AUDIO_EXTENSIONS = {'webm', 'wav', 'mp3', 'pcm'}

# SSL Configuration
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', 'cert.pem')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', 'key.pem')
USE_SSL = os.getenv('USE_SSL', 'false').lower() == 'true'

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_AUDIO_FOLDER, exist_ok=True)
os.makedirs('public', exist_ok=True)

# Load hot words configuration
HOT_WORDS_FILE = 'hot_words.json'
HOT_WORDS = {}

def load_hot_words():
    """Load hot words from configuration file"""
    global HOT_WORDS
    try:
        if os.path.exists(HOT_WORDS_FILE):
            with open(HOT_WORDS_FILE, 'r', encoding='utf-8') as f:
                HOT_WORDS = json.load(f)
                logger.info(f"✅ Loaded {len(HOT_WORDS.get('hotWords', []))} hot words")
                for hw in HOT_WORDS.get('hotWords', []):
                    logger.info(f"   - {hw['word']} (weight: {hw['weight']})")
        else:
            logger.warning(f"Hot words file not found: {HOT_WORDS_FILE}")
            HOT_WORDS = {'hotWords': [], 'settings': {'enabled': False}}
    except Exception as e:
        logger.error(f"Failed to load hot words: {e}")
        HOT_WORDS = {'hotWords': [], 'settings': {'enabled': False}}

# Load hot words on startup
load_hot_words()

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/api/videos', methods=['GET'])
def get_videos():
    """Get all videos with transcripts"""
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify([])

        videos = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('.mp4'):
                video_info = {
                    'name': filename,
                    'url': f'/videos/{filename}'
                }

                # Check for transcript file
                transcript_path = os.path.join(UPLOAD_FOLDER, filename.replace('.mp4', '.txt'))
                if os.path.exists(transcript_path):
                    try:
                        with open(transcript_path, 'r', encoding='utf-8') as f:
                            video_info['transcript'] = f.read().strip()
                            logger.info(f"Loaded transcript for {filename}: {len(video_info['transcript'])} chars")
                    except Exception as e:
                        logger.warning(f"Failed to load transcript for {filename}: {e}")

                videos.append(video_info)

        # Sort videos: introduction.mp4 first, then alphabetically
        def sort_key(video):
            name = video['name'].lower()
            if name == 'introduction.mp4':
                return (0, '')
            else:
                return (1, name)

        videos.sort(key=sort_key)
        logger.info(f"Loaded {len(videos)} videos in order: {[v['name'] for v in videos]}")

        return jsonify(videos)
    except Exception as e:
        logger.error(f"Failed to get videos: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/hot-words', methods=['GET'])
def get_hot_words():
    """Get hot words configuration"""
    try:
        return jsonify(HOT_WORDS)
    except Exception as e:
        logger.error(f"Failed to get hot words: {e}")
        return jsonify({'error': str(e), 'hotWords': [], 'settings': {'enabled': False}}), 500

@app.route('/api/llm-match', methods=['POST'])
def llm_match():
    """Use LLM to match user speech to best video response"""
    try:
        data = request.json
        user_speech = data.get('user_speech', '')
        videos = data.get('videos', [])

        if not user_speech or not videos:
            return jsonify({'error': 'Missing user_speech or videos'}), 400

        logger.info(f"LLM matching: user_speech='{user_speech}', {len(videos)} videos")

        # Build prompt for Qwen
        prompt = build_llm_matching_prompt(user_speech, videos)

        # Call Qwen model
        response = Generation.call(
            model='qwen-turbo',
            prompt=prompt
        )

        if response.status_code != 200:
            logger.error(f"Qwen API error: {response.message}")
            return jsonify({'error': 'LLM API failed', 'message': response.message}), 500

        # Parse LLM response
        llm_output = response.output.text.strip()
        logger.info(f"LLM output: {llm_output}")

        # Extract matched index from LLM response
        matched_index, confidence, reason = parse_llm_response(llm_output, videos)

        logger.info(f"LLM match result: index={matched_index}, confidence={confidence}, reason={reason}")

        return jsonify({
            'matched_index': matched_index,
            'confidence': confidence,
            'reason': reason,
            'llm_output': llm_output
        })

    except Exception as e:
        logger.error(f"LLM matching error: {e}")
        logger.exception(e)
        return jsonify({'error': str(e)}), 500


def build_llm_matching_prompt(user_speech, videos):
    """Build prompt for LLM to match user speech to video responses"""
    prompt = f"""你是一个对话匹配助手。用户说了一句话，你需要从多个视频回复中选择最合适的回应。

用户说: "{user_speech}"

可选的视频回复:
"""

    for i, video in enumerate(videos):
        prompt += f"\n{i}. {video['name']}\n   内容: {video['transcript'][:200]}\n"

    prompt += """
请分析用户的话，选择最合适的视频作为回应。考虑:
1. 对话的连贯性和自然性
2. 情感和语气的匹配
3. 上下文的合理性

请只返回一个JSON格式的回答:
{
  "index": 选中的视频索引(数字),
  "confidence": 置信度(0-1之间的小数),
  "reason": "选择理由(简短说明)"
}

如果没有合适的匹配，返回:
{
  "index": -1,
  "confidence": 0,
  "reason": "没有合适的回应"
}
"""

    return prompt


def parse_llm_response(llm_output, videos):
    """Parse LLM response to extract matched index"""
    try:
        import re

        # Find JSON in the response
        json_match = re.search(r'\{[^}]+\}', llm_output)
        if json_match:
            result = json.loads(json_match.group())
            index = result.get('index', -1)
            confidence = result.get('confidence', 0.95)
            reason = result.get('reason', 'LLM matched')

            # Validate index
            if index >= 0 and index < len(videos):
                return index, confidence, reason

        # Fallback: try to find number in response
        numbers = re.findall(r'\b(\d+)\b', llm_output)
        if numbers:
            index = int(numbers[0])
            if index >= 0 and index < len(videos):
                return index, 0.85, 'Extracted from LLM response'

        return -1, 0, 'No match found'

    except Exception as e:
        logger.error(f"Error parsing LLM response: {e}")
        return -1, 0, f'Parse error: {str(e)}'

# ============================================================================
# WebSocket Streaming Implementation
# ============================================================================

class StreamingRecognitionCallback(RecognitionCallback):
    """Callback handler for streaming recognition results"""

    def __init__(self, session_id):
        self.session_id = session_id
        self.partial_results = []
        self.final_result = None

    def on_open(self):
        """Called when recognition stream opens"""
        logger.info(f"[{self.session_id}] Recognition stream opened")
        socketio.emit('recognition_opened', {
            'session_id': self.session_id,
            'status': 'opened'
        })

    def on_event(self, result):
        """Called for each recognition result (partial or final)"""
        try:
            logger.info(f"[{self.session_id}] Recognition event received")

            # Extract transcript from result
            transcript = self._extract_transcript(result)

            if transcript:
                logger.info(f"[{self.session_id}] 📝 Transcript: {transcript}")

                # Send partial result to client
                socketio.emit('recognition_result', {
                    'session_id': self.session_id,
                    'transcript': transcript,
                    'is_final': False
                })

                self.partial_results.append(transcript)
                self.final_result = transcript
        except Exception as e:
            logger.error(f"[{self.session_id}] Error in on_event: {e}")
            logger.exception(e)

    def on_complete(self):
        """Called when recognition completes"""
        logger.info(f"[{self.session_id}] Recognition completed")

        # Send final result
        final_transcript = self.final_result or ''
        logger.info(f"[{self.session_id}] ✅ Final transcript: {final_transcript}")

        socketio.emit('recognition_complete', {
            'session_id': self.session_id,
            'transcript': final_transcript,
            'is_final': True
        })

    def on_error(self, result):
        """Called on recognition error"""
        logger.error(f"[{self.session_id}] Recognition error: {result}")
        socketio.emit('recognition_error', {
            'session_id': self.session_id,
            'error': str(result)
        })

    def on_close(self):
        """Called when recognition stream closes"""
        logger.info(f"[{self.session_id}] Recognition stream closed")
        socketio.emit('recognition_closed', {
            'session_id': self.session_id,
            'status': 'closed'
        })

    def _extract_transcript(self, result):
        """Extract transcript from recognition result"""
        try:
            if not result:
                return ''

            output = None

            if hasattr(result, 'output'):
                output = result.output
            elif hasattr(result, 'response') and hasattr(result.response, 'output'):
                output = result.response.output
            elif isinstance(result, dict):
                output = result.get('output')

            if not output:
                logger.warning(f"[{self.session_id}] No output in result")
                return ''

            # Try different output formats
            if isinstance(output, dict):
                if 'sentence' in output:
                    sentences = output['sentence']
                    if isinstance(sentences, list):
                        texts = []
                        for sentence in sentences:
                            if isinstance(sentence, dict) and 'text' in sentence:
                                texts.append(sentence['text'])
                        if texts:
                            return ''.join(texts)
                    elif isinstance(sentences, dict) and 'text' in sentences:
                        return sentences['text']

                if 'text' in output and output['text']:
                    return output['text']

            if isinstance(output, str):
                return output

            return ''
        except Exception as e:
            logger.error(f"[{self.session_id}] Error extracting transcript: {e}")
            logger.exception(e)
            return ''

# Store active recognition sessions
active_sessions = {}
sessions_lock = Lock()

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'session_id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

    # Clean up any active recognition session
    with sessions_lock:
        if request.sid in active_sessions:
            try:
                recognition = active_sessions[request.sid]
                recognition.stop()
                del active_sessions[request.sid]
                logger.info(f"Cleaned up recognition session: {request.sid}")
            except Exception as e:
                logger.error(f"Error cleaning up session: {e}")

@socketio.on('start_recognition')
def handle_start_recognition(data=None):
    """Start a new recognition session"""
    session_id = request.sid
    logger.info(f"[{session_id}] Starting recognition session")

    if not DASHSCOPE_API_KEY:
        emit('recognition_error', {
            'error': 'DASHSCOPE_API_KEY not configured'
        })
        return

    try:
        with sessions_lock:
            # Stop any existing session
            if session_id in active_sessions:
                try:
                    active_sessions[session_id].stop()
                except:
                    pass

            # Create new recognition instance with callback
            callback = StreamingRecognitionCallback(session_id)

            # Build hot words list for DashScope
            hot_words_list = []
            if HOT_WORDS.get('settings', {}).get('enabled', True):
                for hw in HOT_WORDS.get('hotWords', []):
                    hot_words_list.append({
                        'word': hw['word'],
                        'weight': hw.get('weight', 5)
                    })

            logger.info(f"[{session_id}] Using {len(hot_words_list)} hot words")

            # Create recognition with hot words
            recognition_kwargs = {
                'model': 'paraformer-realtime-v2',
                'format': 'pcm',
                'sample_rate': 16000,
                'callback': callback
            }

            # Add hot words if available
            if hot_words_list:
                recognition_kwargs['hot_words'] = hot_words_list

            recognition = Recognition(**recognition_kwargs)

            # Start recognition
            recognition.start()

            # Initialize counters
            recognition._audio_frame_count = 0
            recognition._total_bytes_sent = 0

            # Store session
            active_sessions[session_id] = recognition

            logger.info(f"[{session_id}] Recognition started successfully")
            emit('recognition_started', {
                'session_id': session_id,
                'status': 'started'
            })

    except Exception as e:
        logger.error(f"[{session_id}] Failed to start recognition: {e}")
        logger.exception(e)
        emit('recognition_error', {
            'error': str(e)
        })

@socketio.on('audio_data')
def handle_audio_data(data):
    """Receive and process audio data chunks"""
    session_id = request.sid

    try:
        with sessions_lock:
            if session_id not in active_sessions:
                logger.warning(f"[{session_id}] No active recognition session")
                emit('recognition_error', {
                    'error': 'No active recognition session'
                })
                return

            recognition = active_sessions[session_id]

        # data should be Int16Array sent as array of numbers
        if isinstance(data, dict) and 'audio' in data:
            int16_array = data['audio']

            # Log first time we receive data
            if not hasattr(recognition, '_first_data_logged'):
                logger.info(f"[{session_id}] First audio data received: {len(int16_array)} samples")
                logger.info(f"[{session_id}] Sample values (first 10): {int16_array[:10]}")
                recognition._first_data_logged = True

            # Pack as little-endian signed 16-bit integers
            audio_bytes = struct.pack(f'<{len(int16_array)}h', *int16_array)
        elif isinstance(data, bytes):
            audio_bytes = data
        else:
            logger.error(f"[{session_id}] Invalid audio data format: {type(data)}")
            return

        # Send audio frame to DashScope
        recognition.send_audio_frame(audio_bytes)

        # Update counters
        recognition._audio_frame_count += 1
        recognition._total_bytes_sent += len(audio_bytes)

        # Log every 50 frames
        if recognition._audio_frame_count % 50 == 0:
            logger.info(f"[{session_id}] Sent {recognition._audio_frame_count} frames, {recognition._total_bytes_sent} bytes total")

        logger.debug(f"[{session_id}] Sent {len(audio_bytes)} bytes to recognition")

    except Exception as e:
        logger.error(f"[{session_id}] Error processing audio data: {e}")
        logger.exception(e)
        emit('recognition_error', {
            'error': str(e)
        })

@socketio.on('stop_recognition')
def handle_stop_recognition(data=None):
    """Stop the recognition session"""
    session_id = request.sid
    logger.info(f"[{session_id}] Stopping recognition session")

    try:
        with sessions_lock:
            if session_id in active_sessions:
                recognition = active_sessions[session_id]

                # Log final stats
                if hasattr(recognition, '_audio_frame_count'):
                    logger.info(f"[{session_id}] Final stats: {recognition._audio_frame_count} frames, {recognition._total_bytes_sent} bytes")

                recognition.stop()
                del active_sessions[session_id]
                logger.info(f"[{session_id}] Recognition stopped successfully")
                emit('recognition_stopped', {
                    'session_id': session_id,
                    'status': 'stopped'
                })
            else:
                logger.warning(f"[{session_id}] No active session to stop")

    except Exception as e:
        logger.error(f"[{session_id}] Error stopping recognition: {e}")
        logger.exception(e)
        emit('recognition_error', {
            'error': str(e)
        })

if __name__ == '__main__':
    print("=" * 60)
    print("🎬 语音交互视频播放器 - HTTPS 版本")
    print("=" * 60)
    print()
    print("📁 视频目录:", UPLOAD_FOLDER)
    print("🔑 DashScope API Key:", '✅ 已配置' if DASHSCOPE_API_KEY else '❌ 未配置')

    if DASHSCOPE_API_KEY:
        print(f"   API Key 前缀: {DASHSCOPE_API_KEY[:10]}...")

    try:
        sdk_version = dashscope.__version__ if hasattr(dashscope, '__version__') else 'unknown'
        print(f"📦 DashScope SDK 版本: {sdk_version}")
    except:
        print("📦 DashScope SDK 版本: unknown")

    # Check SSL configuration
    if USE_SSL:
        print(f"🔒 SSL 模式: 启用")
        print(f"   证书文件: {SSL_CERT_PATH}")
        print(f"   密钥文件: {SSL_KEY_PATH}")

        if not os.path.exists(SSL_CERT_PATH) or not os.path.exists(SSL_KEY_PATH):
            print()
            print("⚠️  警告: SSL 证书文件不存在!")
            print("   生成自签名证书 (测试用):")
            print("   openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365")
            print()
            print("   或使用 Let's Encrypt (生产环境):")
            print("   sudo certbot certonly --standalone -d yourdomain.com")
            print()
            USE_SSL = False
    else:
        print("🔓 SSL 模式: 禁用 (HTTP)")
        print("   ⚠️  注意: 浏览器可能阻止麦克风访问 (需要 HTTPS 或 localhost)")

    protocol = "https" if USE_SSL else "http"
    print(f"🌐 访问地址: {protocol}://localhost:5000")
    print()

    if not DASHSCOPE_API_KEY:
        print("⚠️  警告: 未配置 DASHSCOPE_API_KEY")
        print("   请创建 .env 文件并添加:")
        print("   DASHSCOPE_API_KEY=sk-your-key-here")
        print()
        print("   获取 API Key: https://dashscope.console.aliyun.com/apiKey")
        print()

    print("💡 提示:")
    print("   - 启用 SSL: 在 .env 中添加 USE_SSL=true")
    print("   - 自定义证书: SSL_CERT_PATH=path/to/cert.pem")
    print("   - 自定义密钥: SSL_KEY_PATH=path/to/key.pem")
    print()
    print("=" * 60)
    print()

    # Run with or without SSL
    if USE_SSL and os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH):
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=True,
            certfile=SSL_CERT_PATH,
            keyfile=SSL_KEY_PATH,
            allow_unsafe_werkzeug=True
        )
    else:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=True,
            allow_unsafe_werkzeug=True
        )
