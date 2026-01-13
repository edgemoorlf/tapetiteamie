import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import dashscope
from dashscope.audio.asr import Recognition
from dotenv import load_dotenv
import tempfile
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

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
    """获取所有视频列表"""
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify([])
        
        videos = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('.mp4'):
                videos.append({
                    'name': filename,
                    'url': f'/videos/{filename}'
                })
        
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
        
        # 调用识别 - 传入二进制数据
        # result = recognition.call(audio_data)
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
    
    app.run(host='0.0.0.0', port=5001, debug=True)