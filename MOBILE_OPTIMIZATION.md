# Mobile Optimization Guide

## Overview

The web app has been optimized for mobile devices with responsive layout and video compression capabilities.

## Mobile Layout Changes

### Responsive CSS Added

The app now includes mobile-responsive CSS with two breakpoints:

1. **Tablets and small screens** (≤768px)
2. **Mobile phones** (≤480px)

### Key Mobile Optimizations

#### 1. Touch-Friendly Buttons
- Minimum button height: 48px (Apple/Google recommendation)
- Larger tap targets for easier interaction
- Full-width buttons on small screens

#### 2. Optimized Layout
- Reduced padding and margins for more screen space
- Smaller font sizes for better fit
- Adjusted video container for mobile aspect ratios

#### 3. Improved Readability
- Scaled down heading sizes
- Adjusted transcript log height (150px on tablet, 120px on phone)
- Smaller but readable font sizes

#### 4. Vertical Layout on Small Screens
- Controls stack vertically on phones (≤480px)
- Full-width buttons for easier tapping
- Optimized spacing between elements

## Testing Mobile Layout

### Using Browser DevTools

**Chrome/Edge:**
1. Open DevTools (F12 or Cmd+Option+I)
2. Click "Toggle device toolbar" (Cmd+Shift+M)
3. Select device: iPhone 12, Pixel 5, etc.
4. Test portrait and landscape orientations

**Firefox:**
1. Open DevTools (F12)
2. Click "Responsive Design Mode" (Cmd+Option+M)
3. Select device or custom dimensions

### Test on Real Device

**Option 1: Same Network**
1. Find your computer's IP address:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "

   # Or use
   hostname -I
   ```

2. Start server:
   ```bash
   python server.py
   ```

3. On mobile browser, visit:
   ```
   http://YOUR_IP:5000
   ```
   Example: `http://192.168.1.100:5000`

**Option 2: ngrok (Public URL)**
1. Install ngrok: https://ngrok.com/download

2. Start server:
   ```bash
   python server.py
   ```

3. In another terminal:
   ```bash
   ngrok http 5000
   ```

4. Use the ngrok URL on your mobile device

## Video Compression for Mobile

### Why Compress Videos?

**Benefits:**
- ✅ Faster loading on mobile networks
- ✅ Less data consumption
- ✅ Smoother playback
- ✅ Better user experience

**File Size Reduction:**
- Original: ~50 MB per 2-minute video
- Compressed: ~20 MB per 2-minute video
- **Savings: 60%**

### Quick Compression

**Single video:**
```bash
ffmpeg -i videos/introduction.mp4 -vf scale=720:-2 -c:v libx264 -crf 28 -preset medium -c:a aac -b:a 96k videos_mobile/introduction.mp4
```

**All videos:**
```bash
python compress_videos.py
```

### Compression Script Usage

**Basic usage (recommended):**
```bash
python compress_videos.py
```

**High quality (less compression):**
```bash
python compress_videos.py --quality high
```

**Maximum compression (smallest files):**
```bash
python compress_videos.py --quality maximum
```

**Custom directories:**
```bash
python compress_videos.py --input my_videos --output compressed
```

### Quality Levels

| Quality | Resolution | File Size | Use Case |
|---------|------------|-----------|----------|
| High | 1280px | ~30 MB | WiFi, tablets |
| **Balanced** | **720px** | **~20 MB** | **4G/5G (Recommended)** |
| Maximum | 480px | ~10 MB | 3G, data-limited |

### Deployment Options

#### Option 1: Replace Original Videos

**Backup first:**
```bash
cp -r videos videos_backup
```

**Replace with compressed:**
```bash
rm videos/*.mp4
cp videos_mobile/*.mp4 videos/
```

**Restart server:**
```bash
python server.py
```

#### Option 2: Serve Based on Device

Modify `server.py` to detect mobile devices:

```python
from flask import request

@app.route('/api/videos')
def get_videos():
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone'])

    video_dir = 'videos_mobile' if is_mobile else 'videos'

    # Load videos from appropriate directory
    videos = []
    for filename in sorted(os.listdir(video_dir)):
        if filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            videos.append({
                'name': filename,
                'url': f'/videos/{filename}'
            })

    return jsonify(videos)
```

## Mobile-Specific Features

### 1. Viewport Configuration

Already included in HTML:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

This ensures proper scaling on mobile devices.

### 2. Touch Events

The app uses standard click events which work with touch on mobile.

### 3. Audio Context on Mobile

**Important:** Mobile browsers require user interaction before AudioContext can start.

The app handles this by:
- Starting AudioContext on button click
- Showing appropriate error messages if blocked

### 4. Microphone Permissions

Mobile browsers will prompt for microphone access when:
- User clicks "开始语音识别" button
- First time only (permission is remembered)

## Mobile Browser Compatibility

### Supported Browsers

| Browser | Voice Recognition | Video Playback | Notes |
|---------|-------------------|----------------|-------|
| Chrome (Android) | ✅ DashScope + Browser | ✅ | Full support |
| Safari (iOS) | ⚠️ DashScope only | ✅ | Web Speech API limited |
| Firefox (Android) | ✅ DashScope only | ✅ | No Web Speech API |
| Edge (Android) | ✅ DashScope + Browser | ✅ | Full support |

### Recommendations

**For best mobile experience:**
1. Use Chrome or Edge on Android
2. Use Safari on iOS
3. Enable DashScope mode for better accuracy
4. Use compressed videos for faster loading

## Performance Optimization

### 1. Video Preloading on Mobile

The app preloads all videos at startup. On mobile:
- **WiFi**: Fast preloading (~5-10 seconds for 9 videos)
- **4G/5G**: Moderate (~15-30 seconds)
- **3G**: Slow (~1-2 minutes)

**Recommendation:** Use compressed videos for mobile networks.

### 2. Network Detection (Future Enhancement)

Could add network speed detection:
```javascript
// Check connection type
const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
if (connection) {
  const type = connection.effectiveType; // '4g', '3g', '2g', 'slow-2g'
  console.log('Network type:', type);

  // Adjust preloading strategy based on network
  if (type === '3g' || type === 'slow-2g') {
    // Preload only next 2 videos
  } else {
    // Preload all videos
  }
}
```

### 3. Lazy Loading (Alternative Approach)

For very slow connections, could implement lazy loading:
- Preload only first video
- Load others on-demand
- Show loading indicator during switch

## Mobile Testing Checklist

### Layout Testing
- [ ] App fits screen without horizontal scroll
- [ ] All buttons are easily tappable (48px minimum)
- [ ] Text is readable without zooming
- [ ] Video player scales properly
- [ ] Transcript log is scrollable
- [ ] Video list is accessible

### Functionality Testing
- [ ] Microphone permission prompt works
- [ ] Voice recognition starts/stops correctly
- [ ] Video switching works smoothly
- [ ] Transcript logging displays correctly
- [ ] Mode toggle works (DashScope/Browser)
- [ ] Video preloading completes

### Performance Testing
- [ ] Videos load within acceptable time
- [ ] No lag during video switching
- [ ] App remains responsive during recognition
- [ ] Memory usage is acceptable
- [ ] Battery drain is reasonable

### Network Testing
- [ ] Works on WiFi
- [ ] Works on 4G/5G
- [ ] Graceful degradation on 3G
- [ ] Handles network interruptions

## Troubleshooting

### Issue: Layout looks broken on mobile

**Solution:** Clear browser cache and reload:
```
Settings → Clear browsing data → Cached images and files
```

### Issue: Videos won't play on iPhone

**Possible causes:**
1. Video format not supported
2. Autoplay blocked

**Solution:**
- Use H.264 codec (already done in compression script)
- User must tap to start video (iOS requirement)

### Issue: Microphone not working on mobile

**Possible causes:**
1. Permission denied
2. HTTPS required (some browsers)
3. AudioContext blocked

**Solution:**
1. Check browser permissions
2. Use HTTPS or localhost
3. Ensure user interaction before starting

### Issue: Videos load too slowly

**Solution:**
1. Compress videos: `python compress_videos.py`
2. Use lower quality: `python compress_videos.py --quality maximum`
3. Reduce number of preloaded videos

### Issue: App uses too much data

**Solution:**
1. Use compressed videos
2. Implement lazy loading
3. Add WiFi-only mode

## Mobile-Specific CSS Breakpoints

### Current Breakpoints

```css
/* Tablets and small screens */
@media (max-width: 768px) {
  /* Optimized for tablets, landscape phones */
}

/* Mobile phones */
@media (max-width: 480px) {
  /* Optimized for portrait phones */
}
```

### Customizing Breakpoints

To adjust for specific devices, modify in `public/index.html`:

```css
/* Large phones (iPhone 12 Pro Max, etc.) */
@media (max-width: 428px) {
  /* Custom styles */
}

/* Small phones (iPhone SE, etc.) */
@media (max-width: 375px) {
  /* Custom styles */
}
```

## Best Practices

### 1. Always Test on Real Devices

Browser DevTools are good for layout, but test on real devices for:
- Touch interactions
- Performance
- Network conditions
- Battery usage

### 2. Optimize for Portrait Mode

Most users hold phones vertically:
- Design for portrait first
- Landscape is secondary

### 3. Minimize Data Usage

Mobile users often have limited data:
- Compress videos
- Lazy load when possible
- Show data usage warnings

### 4. Handle Interruptions

Mobile apps get interrupted frequently:
- Save state when app goes to background
- Resume gracefully when returning
- Handle phone calls, notifications

### 5. Battery Considerations

Voice recognition and video playback drain battery:
- Allow users to pause/stop easily
- Don't keep microphone active unnecessarily
- Optimize video encoding

## Summary

✅ **Mobile layout optimized:**
- Responsive CSS for all screen sizes
- Touch-friendly buttons (48px minimum)
- Vertical layout on small screens
- Optimized spacing and fonts

✅ **Video compression ready:**
- `compress_videos.py` script included
- 60% file size reduction
- Maintains good quality
- Easy batch processing

✅ **Testing tools provided:**
- Browser DevTools instructions
- Real device testing guide
- ngrok setup for remote testing

✅ **Performance optimized:**
- Video preloading for smooth playback
- Compressed videos for faster loading
- Mobile-friendly network handling

## Next Steps

1. **Test on your mobile device:**
   ```bash
   python server.py
   # Visit http://YOUR_IP:5000 on mobile
   ```

2. **Compress videos:**
   ```bash
   python compress_videos.py
   ```

3. **Deploy compressed videos:**
   ```bash
   mv videos videos_backup
   mv videos_mobile videos
   python server.py
   ```

4. **Test and iterate:**
   - Check layout on different devices
   - Verify video loading speed
   - Test voice recognition
   - Gather user feedback

Your app is now mobile-ready! 📱✨
