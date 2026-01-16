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

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 配置
DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY')
dashscope.api_key = DASHSCOPE_API_KEY

UPLOAD_FOLDER = 'videos'
TEMP_AUDIO_FOLDER = 'temp_audio'
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov'}
ALLOWED_AUDIO_EXTENSIONS = {'webm', 'wav', 'mp3', 'pcm'}

# 创建必要的目录
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_AUDIO_FOLDER, exist_ok=True)
os.makedirs('public', exist_ok=True)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取所有视频列表及其字幕"""
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

                # Check for transcript file (.txt with same name)
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
                return (0, '')  # First priority
            else:
                return (1, name)  # Alphabetical order

        videos.sort(key=sort_key)

        logger.info(f"Loaded {len(videos)} videos in order: {[v['name'] for v in videos]}")

        return jsonify(videos)
    except Exception as e:
        logger.error(f"获取视频列表失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/videos/<path:filename>')
def serve_video(filename):
    """提供视频文件"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/api/upload', methods=['POST'])
def upload_video():
    """上传视频"""
    if 'video' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        return jsonify({
            'name': filename,
            'url': f'/videos/{filename}'
        })
    
    return jsonify({'error': '不支持的文件格式'}), 400

@app.route('/api/speech-to-text', methods=['POST'])
def speech_to_text():
    """使用 DashScope SDK 进行语音识别"""
    logger.info("收到语音识别请求")
    
    if not DASHSCOPE_API_KEY:
        logger.error("未配置 DASHSCOPE_API_KEY")
        return jsonify({
            'error': '未配置 DASHSCOPE_API_KEY',
            'message': '请在 .env 文件中设置 DASHSCOPE_API_KEY',
            'transcript': ''
        }), 500
    
    if 'audio' not in request.files:
        logger.error("没有收到音频文件")
        return jsonify({
            'error': '没有音频文件',
            'transcript': ''
        }), 400
    
    audio_file = request.files['audio']
    
    # 保存临时音频文件
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, 
        suffix='.pcm', 
        dir=TEMP_AUDIO_FOLDER
    )
    temp_filepath = temp_file.name
    temp_file.close()  # 关闭文件以便写入
    
    try:
        # 保存上传的音频
        audio_file.save(temp_filepath)
        file_size = os.path.getsize(temp_filepath)
        logger.info(f"音频文件路径: {temp_filepath}")
        logger.info(f"音频文件大小: {file_size} bytes")
        
        # 使用 DashScope SDK 进行识别
        logger.info("正在调用 DashScope ASR API...")
        
        # 创建 Recognition 对象
        recognition = Recognition(
            model='paraformer-realtime-v2',
            format='pcm',
            sample_rate=16000,
            callback=None  # 同步调用
        )
        
        # 读取音频文件内容（作为二进制数据）
        with open(temp_filepath, 'rb') as f:
            audio_data = f.read()
            logger.info(f"音频数据长度: {len(audio_data)} bytes")

        result = recognition.call(temp_filepath)  # ✅ 传入 str
        
        logger.info(f"DashScope API 响应状态: {result.get('status_code', 'unknown')}")
        logger.info(f"DashScope API 完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 检查是否有错误
        if isinstance(result, dict) and result.get('status_code') != 200:
            error_msg = result.get('message', '未知错误')
            logger.error(f"API 返回错误: {error_msg}")
            return jsonify({
                'error': 'API 调用失败',
                'message': error_msg,
                'transcript': '',
                'raw': result
            }), 500
        
        # 提取识别结果
        transcript = extract_transcript(result)
        
        if not transcript or transcript.strip() == '':
            logger.info("识别结果为空")
            return jsonify({
                'transcript': '',
                'message': '未能识别出语音，请确保清晰说话并靠近麦克风',
                'raw': result
            })
        
        logger.info(f"✅ 识别成功: {transcript}")
        return jsonify({
            'transcript': transcript.strip(),
            'raw': result
        })
        
    except Exception as e:
        logger.error(f"❌ 语音识别失败: {str(e)}")
        logger.exception(e)
        
        return jsonify({
            'error': '语音识别失败',
            'message': str(e),
            'transcript': ''
        }), 500
        
    finally:
        # 清理临时文件
        try:
            if os.path.exists(temp_filepath):
                os.unlink(temp_filepath)
                logger.info("已删除临时音频文件")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")

def extract_transcript(result):
    """从 DashScope 响应中提取识别文本"""
    if not result:
        return ''
    
    try:
        # 确保 result 是字典
        if not isinstance(result, dict):
            logger.warning(f"响应不是字典类型: {type(result)}")
            return ''
        
        # 检查是否有错误状态码
        status_code = result.get('status_code')
        if status_code and status_code != 200:
            logger.error(f"API 返回错误状态码: {status_code}")
            return ''
        
        # 尝试从 output 中提取
        output = result.get('output')
        if not output:
            logger.warning("响应中没有 output 字段")
            return ''
        
        # 方式1: output.text (最常见)
        if isinstance(output, dict) and 'text' in output:
            text = output['text']
            if isinstance(text, str) and text:
                logger.info(f"从 output.text 提取: {text}")
                return text
        
        # 方式2: output.sentence.text
        if isinstance(output, dict) and 'sentence' in output:
            sentence = output['sentence']
            if isinstance(sentence, dict) and 'text' in sentence:
                text = sentence['text']
                if isinstance(text, str) and text:
                    logger.info(f"从 output.sentence.text 提取: {text}")
                    return text
        
        # 方式3: output 直接是字符串
        if isinstance(output, str) and output:
            logger.info(f"output 直接是字符串: {output}")
            return output
        
        # 方式4: output.results 数组
        if isinstance(output, dict) and 'results' in output:
            results = output['results']
            if isinstance(results, list) and len(results) > 0:
                texts = []
                for r in results:
                    if isinstance(r, dict):
                        # 尝试多个可能的字段名
                        text = (r.get('text') or 
                               r.get('transcription_text') or 
                               r.get('transcript') or
                               '')
                        
                        # 如果有嵌套的 sentence
                        if not text and 'sentence' in r:
                            sentence = r['sentence']
                            if isinstance(sentence, dict):
                                text = sentence.get('text', '')
                        
                        if text and isinstance(text, str):
                            texts.append(text)
                
                if texts:
                    combined = ''.join(texts)
                    logger.info(f"从 output.results 提取: {combined}")
                    return combined
        
        logger.warning(f"无法从响应中提取文本，响应结构: {json.dumps(result, ensure_ascii=False)[:500]}")
        return ''
        
    except Exception as e:
        logger.error(f"提取文本时出错: {e}")
        logger.exception(e)
        return ''

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'dashscopeConfigured': bool(DASHSCOPE_API_KEY),
        'sdkVersion': dashscope.__version__ if hasattr(dashscope, '__version__') else 'unknown',
        'timestamp': os.popen('date').read().strip()
    })

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
        # Try to parse as JSON
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

            # For streaming callbacks, result is RecognitionResult object
            # Try to access output directly
            output = None

            if hasattr(result, 'output'):
                output = result.output
            elif hasattr(result, 'response') and hasattr(result.response, 'output'):
                output = result.response.output
            elif isinstance(result, dict):
                output = result.get('output')

            if not output:
                logger.warning(f"[{self.session_id}] No output in result: {type(result)}, {dir(result)}")
                return ''

            # Try different output formats
            if isinstance(output, dict):
                # Method 1: output.sentence array (for file-based)
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

                # Method 2: output.text (most common for streaming)
                if 'text' in output and output['text']:
                    return output['text']

            # Method 3: output is string
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
            recognition = Recognition(
                model='paraformer-realtime-v2',
                format='pcm',
                sample_rate=16000,
                callback=callback
            )

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
            # Convert Int16 array to bytes
            # Int16 values are -32768 to 32767, need to convert to bytes properly
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
    print("🎬 语音交互视频播放器 - Python 版本")
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
    
    print("🌐 访问地址: http://localhost:5001")
    print()
    
    if not DASHSCOPE_API_KEY:
        print("⚠️  警告: 未配置 DASHSCOPE_API_KEY")
        print("   请创建 .env 文件并添加:")
        print("   DASHSCOPE_API_KEY=sk-your-key-here")
        print()
        print("   获取 API Key: https://dashscope.console.aliyun.com/apiKey")
        print()
    
    print("💡 提示:")
    print("   - 测试配置: python test_dashscope.py")
    print("   - 测试音频: python test_audio.py <音频文件>")
    print("   - 查看日志: 直接查看控制台输出")
    print()
    print("=" * 60)
    print()

    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)