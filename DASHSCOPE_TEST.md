# DashScope Streaming Test Guide

## Quick Test

### 1. Start the Server

```bash
python server.py
```

**Expected output:**
```
🎬 语音交互视频播放器 - Python 版本
📁 视频目录: videos
🔑 DashScope API Key: ✅ 已配置
🌐 访问地址: http://localhost:5001
```

### 2. Open Browser

Navigate to: http://localhost:5001

### 3. Test DashScope Mode

1. **Ensure DashScope mode is selected**
   - Button should show: "模式: DashScope"
   - If not, click the button to switch

2. **Click "🎤 测试语音" button**

3. **Speak clearly in Chinese**
   - Say something like: "大家好" or "视频一"
   - Speak for 2-3 seconds

4. **Check what happens**

## What to Look For

### ✅ Success Indicators

**In Browser:**
- Voice prompt appears with microphone icon
- Status shows: "🎤 正在听... (DashScope 流式识别)"
- Transcript log shows partial results in real-time
- Final result appears after 5 seconds
- Video switches if match found

**In Server Console:**
```
INFO:__main__:[session_id] Starting recognition session
INFO:__main__:[session_id] Recognition stream opened
INFO:__main__:[session_id] Recognition started successfully
INFO:__main__:[session_id] First audio data received: 4096 samples
INFO:__main__:[session_id] Sample values (first 10): [123, -456, 789, ...]
INFO:__main__:[session_id] Sent 50 frames, 409600 bytes total
INFO:__main__:[session_id] Recognition event received
INFO:__main__:[session_id] 📝 Transcript: 大家好
INFO:__main__:[session_id] ✅ Final transcript: 大家好
INFO:__main__:[session_id] Final stats: 195 frames, 1597440 bytes
INFO:__main__:[session_id] Recognition stopped successfully
```

### ❌ Failure Indicators

**Problem 1: No audio data received**
```
INFO:__main__:[session_id] Recognition started successfully
INFO:__main__:[session_id] Stopping recognition session
INFO:__main__:[session_id] Final stats: 0 frames, 0 bytes
```
**Solution:** Check browser microphone permissions

**Problem 2: Audio data but no recognition**
```
INFO:__main__:[session_id] Sent 195 frames, 1597440 bytes
INFO:__main__:[session_id] Recognition completed
# No transcript logged
```
**Solution:** Speak louder or closer to microphone

**Problem 3: API Error**
```
ERROR:dashscope:Request failed, request_id: xxx, http_code: 44 error_name: NO_VALID_AUDIO_ERROR
```
**Solution:** Audio format issue - check logs for sample values

## Detailed Debugging

### Check Browser Console

Open browser DevTools (F12) and check Console tab:

**Expected logs:**
```
WebSocket connected: {session_id: "..."}
Recognition started: {session_id: "...", status: "started"}
[VideoMatcher] ✅ Match found: {...}
```

**Error logs:**
```
Recognition error: {error: "..."}
```

### Check Server Logs

**Key log messages to look for:**

1. **Session Start:**
```
INFO:__main__:[session_id] Starting recognition session
INFO:__main__:[session_id] Recognition stream opened
INFO:__main__:[session_id] Recognition started successfully
```

2. **Audio Data Flow:**
```
INFO:__main__:[session_id] First audio data received: 4096 samples
INFO:__main__:[session_id] Sample values (first 10): [...]
INFO:__main__:[session_id] Sent 50 frames, 409600 bytes total
```

3. **Recognition Results:**
```
INFO:__main__:[session_id] Recognition event received
INFO:__main__:[session_id] 📝 Transcript: 大家好
INFO:__main__:[session_id] ✅ Final transcript: 大家好
```

4. **Session End:**
```
INFO:__main__:[session_id] Final stats: 195 frames, 1597440 bytes
INFO:__main__:[session_id] Recognition stopped successfully
```

### Check Transcript Log Panel

In the browser UI, check the "📝 识别记录" panel:

**Expected entries:**
```
14:23:45 [DashScope] 系统: WebSocket 已连接
14:23:50 [DashScope] 系统: 开始 DashScope 流式识别
14:23:52 [DashScope] 部分结果: 大家
14:23:53 [DashScope] 部分结果: 大家好
14:23:55 [DashScope] 最终结果: 大家好
14:23:55 [DashScope] 匹配结果: 视频 #1 (Transcript Match, 置信度: 100.0%)
```

## Common Issues

### Issue 1: Microphone Not Working

**Symptoms:**
- No audio data in server logs
- Browser doesn't show microphone permission prompt

**Solutions:**
1. Check browser microphone permissions
2. Try different browser (Chrome/Edge recommended)
3. Check system microphone settings
4. Try HTTPS instead of HTTP (some browsers require it)

### Issue 2: Audio Data Sent But No Recognition

**Symptoms:**
- Server logs show audio frames sent
- No transcript in logs
- "NO_VALID_AUDIO_ERROR" from DashScope

**Solutions:**
1. Check sample values in logs - should not be all zeros
2. Speak louder and clearer
3. Check microphone is not muted
4. Try different microphone

### Issue 3: WebSocket Connection Failed

**Symptoms:**
- Browser console shows connection errors
- No "WebSocket connected" message

**Solutions:**
1. Check server is running
2. Check firewall settings
3. Try restarting server
4. Check port 5001 is not blocked

### Issue 4: Recognition Works But Low Accuracy

**Symptoms:**
- Gets transcript but wrong words
- Confidence score is low

**Solutions:**
1. Speak more clearly
2. Reduce background noise
3. Speak closer to microphone
4. Use standard Mandarin pronunciation

## Test Scenarios

### Test 1: Basic Recognition

**Steps:**
1. Click "🎤 测试语音"
2. Say: "大家好"
3. Wait for result

**Expected:**
- Transcript: "大家好"
- Confidence: >90%

### Test 2: Video Matching

**Steps:**
1. Ensure you have `introduction.mp4` in videos folder
2. Click "🎤 测试语音"
3. Say: "introduction"

**Expected:**
- Matches introduction.mp4
- Video switches and plays

### Test 3: Numeric Matching

**Steps:**
1. Click "🎤 测试语音"
2. Say: "视频一" or "第一个"

**Expected:**
- Matches first video
- Video switches and plays

### Test 4: Transcript Matching

**Steps:**
1. Create `introduction.txt` with: "大家好，欢迎来到我的频道"
2. Restart server
3. Click "🎤 测试语音"
4. Say: "大家好欢迎"

**Expected:**
- Matches introduction.mp4 via transcript
- High confidence (>90%)

## Performance Metrics

**Normal operation:**
- Audio frames: ~195 frames in 5 seconds
- Total bytes: ~1.6 MB in 5 seconds
- Frame rate: ~39 frames/second
- Bytes per frame: ~8192 bytes (4096 samples × 2 bytes)

**If metrics are off:**
- Too few frames: Microphone issue or connection problem
- Too many frames: Buffer size issue
- Zero bytes: No audio data being captured

## Comparison: DashScope vs Browser Mode

### Test Both Modes

1. **Test DashScope Mode** (as above)
2. **Switch to Browser Mode**
   - Click "模式" button
   - Should show: "模式: 浏览器"
3. **Test Browser Mode**
   - Click "🎤 测试语音"
   - Say: "大家好"
   - Should work immediately (no 5-second wait)

**Expected differences:**
- Browser mode: Faster, auto-stops on silence
- DashScope mode: Fixed 5-second recording, more control

## Summary

✅ **Working correctly if:**
- Server logs show audio frames being sent
- Server logs show recognition events with transcripts
- Browser shows partial and final results
- Videos match and play correctly

❌ **Not working if:**
- No audio frames in server logs
- No recognition events
- Empty transcripts
- API errors in logs

**Next steps if not working:**
1. Check all logs (server + browser console)
2. Verify microphone permissions
3. Test with Browser mode first (simpler)
4. Check API key is valid
5. Try speaking louder/clearer
