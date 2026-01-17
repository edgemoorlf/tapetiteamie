# Hot Words Configuration Guide

## Overview

Hot words are custom keywords that the voice recognition system prioritizes. They help the ASR (Automatic Speech Recognition) engine recognize specific phrases more accurately and reliably.

## What Are Hot Words?

Hot words are:
- **Priority keywords** that the system should recognize with higher confidence
- **Domain-specific terms** relevant to your application
- **Trigger phrases** that users commonly say
- **Weighted** by importance (higher weight = higher priority)

## Default Hot Words

The system comes with pre-configured hot words optimized for the video player:

| Word | Pinyin | Weight | Purpose |
|------|--------|--------|---------|
| 播放 | bō fàng | 8 | Play command |
| 视频 | shì pín | 8 | Video reference |
| 下一个 | xià yī gè | 8 | Next video |
| 上一个 | shàng yī gè | 8 | Previous video |
| 暂停 | zàn tíng | 8 | Pause command |
| 继续 | jì xù | 8 | Resume command |

## Configuration File

Hot words are stored in `hot_words.json`:

```json
{
  "hotWords": [
    {
      "word": "神经病",
      "pinyin": "shén jīn bìng",
      "weight": 10,
      "description": "mind disorder"
    },
    {
      "word": "你有问题",
      "pinyin": "nǐ yoǔ wèn tí",
      "weight": 10,
      "description": "something wrong with you"
    },
  ],
  "settings": {
    "enabled": true,
    "minConfidence": 0.5,
    "maxHotWords": 20,
    "description": "Hot words configuration for voice recognition"
  }
}
```

## How Hot Words Work

### DashScope Integration

When you start voice recognition:

1. **Load hot words** from `hot_words.json`
2. **Build hot words list** with word and weight
3. **Pass to DashScope** ASR engine
4. **Recognition prioritizes** these words during processing
5. **Results are more accurate** for hot words

**Example:**
```python
# Server-side (server.py)
hot_words_list = [
    {'word': '播放', 'weight': 8}
]

recognition = Recognition(
    model='paraformer-realtime-v2',
    format='pcm',
    sample_rate=16000,
    callback=callback,
    hot_words=hot_words_list  # ← Pass hot words
)
```

### Weight System

**Weight Range:** 1-15 (higher = more important)

- **15**: Maximum priority (main character name)
- **10**: High priority (character name)
- **8**: Normal priority (commands)
- **5**: Low priority (optional words)
- **1**: Minimal priority (fallback)

**Effect:**
- Higher weight → More likely to be recognized
- Higher weight → Better accuracy for that word
- Higher weight → Prioritized in ambiguous cases

## Customizing Hot Words

### Edit Configuration File

**File:** `hot_words.json`

**Example: Add new hot words**

```json
{
  "hotWords": [
    {
      "word": "虚里",
      "pinyin": "xū lǐ",
      "weight": 10,
      "description": "Character name"
    },
    {
      "word": "我爱你",
      "pinyin": "wǒ ài nǐ",
      "weight": 12,
      "description": "Love confession"
    },
    {
      "word": "再见",
      "pinyin": "zài jiàn",
      "weight": 8,
      "description": "Goodbye"
    }
  ],
  "settings": {
    "enabled": true,
    "minConfidence": 0.5,
    "maxHotWords": 20
  }
}
```

### Update via API

**Endpoint:** `POST /api/hot-words`

**Request:**
```bash
curl -X POST http://localhost:5001/api/hot-words \
  -H "Content-Type: application/json" \
  -d '{
    "hotWords": [
      {
        "word": "虚里",
        "pinyin": "xū lǐ",
        "weight": 10,
        "description": "Character name"
      }
    ],
    "settings": {
      "enabled": true,
      "minConfidence": 0.5,
      "maxHotWords": 20
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Updated 1 hot words",
  "hotWords": { ... }
}
```

### Get Current Hot Words

**Endpoint:** `GET /api/hot-words`

**Request:**
```bash
curl http://localhost:5001/api/hot-words
```

**Response:**
```json
{
  "hotWords": [
    {
      "word": "虚里",
      "pinyin": "xū lǐ",
      "weight": 10,
      "description": "Character name"
    }
  ],
  "settings": {
    "enabled": true,
    "minConfidence": 0.5,
    "maxHotWords": 20
  }
}
```

## Best Practices

### 1. Choose Relevant Words

**Good:**
- Character names
- Common commands
- Domain-specific terms
- Frequently used phrases

**Bad:**
- Generic words (太, 的, 了)
- Very long phrases
- Rarely used terms
- Ambiguous words

### 2. Set Appropriate Weights

**High Weight (12-15):**
- Main character names
- Critical commands
- Most important phrases

**Medium Weight (8-10):**
- Secondary commands
- Common variations
- Important terms

**Low Weight (5-7):**
- Optional words
- Rare variations
- Fallback terms

### 3. Limit Number of Hot Words

**Recommended:** 5-15 hot words

**Why:**
- Too many dilutes effectiveness
- Performance impact
- Conflicting priorities
- Reduced accuracy

**Maximum:** 20 hot words (configurable)

### 4. Test and Iterate

1. **Start small** - Add 5-10 hot words
2. **Test recognition** - Try voice commands
3. **Monitor accuracy** - Check console logs
4. **Adjust weights** - Fine-tune based on results
5. **Add more** - Gradually expand as needed

## Troubleshooting

### Issue: Hot words not working

**Possible Causes:**
1. Hot words disabled in settings
2. File not found or invalid JSON
3. Server not restarted after changes
4. DashScope API doesn't support hot words

**Solutions:**
1. Check `settings.enabled` is `true`
2. Validate JSON syntax: `python -m json.tool hot_words.json`
3. Restart server: `python server.py`
4. Check server logs for hot words loading

### Issue: Recognition accuracy decreased

**Possible Causes:**
1. Too many hot words
2. Conflicting hot words
3. Weights too high
4. Hot words too similar

**Solutions:**
1. Reduce number of hot words
2. Remove conflicting words
3. Lower weights (try 5-8)
4. Use more distinct words

### Issue: Specific words not recognized

**Possible Causes:**
1. Word not in hot words list
2. Weight too low
3. Pronunciation unclear
4. Similar sounding words

**Solutions:**
1. Add word to hot words
2. Increase weight
3. Speak more clearly
4. Use pinyin to verify pronunciation

## Advanced Configuration

### Disable Hot Words

**In `hot_words.json`:**
```json
{
  "settings": {
    "enabled": false
  }
}
```

**Or via API:**
```bash
curl -X POST http://localhost:5001/api/hot-words \
  -H "Content-Type: application/json" \
  -d '{"hotWords": [], "settings": {"enabled": false}}'
```

### Dynamic Hot Words

**Load from database:**
```python
# In server.py
def load_hot_words_from_db():
    # Query database for hot words
    # Return formatted list
    pass
```

**Load from environment:**
```python
# In server.py
HOT_WORDS_ENV = os.getenv('HOT_WORDS_JSON')
if HOT_WORDS_ENV:
    HOT_WORDS = json.loads(HOT_WORDS_ENV)
```

### Per-Session Hot Words

**Send hot words with recognition request:**
```javascript
// In frontend
this.socket.emit('start_recognition', {
  hotWords: [
    { word: '虚里', weight: 10 },
    { word: '播放', weight: 8 }
  ]
});
```

**Handle in server:**
```python
@socketio.on('start_recognition')
def handle_start_recognition(data=None):
    session_hot_words = data.get('hotWords', []) if data else []
    # Use session-specific hot words
```

## Performance Impact

### Memory Usage
- Minimal impact (hot words stored in memory)
- ~1KB per hot word
- 10 hot words ≈ 10KB

### Recognition Speed
- Negligible impact
- DashScope handles optimization
- May slightly improve speed (prioritized words)

### Network Usage
- Hot words sent once per session
- ~1KB per session
- No ongoing overhead

## Monitoring

### Check Hot Words Loading

**Server logs:**
```
✅ Loaded 8 hot words
   - 虚里 (weight: 10)
   - 虚里同学 (weight: 15)
   - 播放 (weight: 8)
   ...
```

### Check Recognition with Hot Words

**Server logs:**
```
[session_id] Using 8 hot words
[session_id] Recognition started successfully
```

### Browser Console

**Check hot words loaded:**
```javascript
console.log('✅ Loaded 8 hot words');
console.log('   - 虚里 (weight: 10)');
```

## Examples

### Example 1: Character-Focused

```json
{
  "hotWords": [
    { "word": "虚里", "weight": 15 },
    { "word": "虚里同学", "weight": 15 },
    { "word": "我爱你", "weight": 12 },
    { "word": "再见", "weight": 10 }
  ]
}
```

### Example 2: Command-Focused

```json
{
  "hotWords": [
    { "word": "播放", "weight": 12 },
    { "word": "暂停", "weight": 12 },
    { "word": "下一个", "weight": 10 },
    { "word": "上一个", "weight": 10 },
    { "word": "继续", "weight": 10 }
  ]
}
```

### Example 3: Balanced

```json
{
  "hotWords": [
    { "word": "虚里", "weight": 12 },
    { "word": "播放", "weight": 10 },
    { "word": "暂停", "weight": 10 },
    { "word": "下一个", "weight": 8 },
    { "word": "上一个", "weight": 8 },
    { "word": "我爱你", "weight": 10 },
    { "word": "再见", "weight": 8 }
  ]
}
```

## Summary

✅ **Hot words improve recognition accuracy**
✅ **Easy to configure via JSON file**
✅ **Can be updated via API**
✅ **Minimal performance impact**
✅ **Supports weighted priorities**
✅ **Works with DashScope ASR**

Hot words are a powerful way to optimize voice recognition for your specific use case!
