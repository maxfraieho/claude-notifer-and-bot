# 📸 Image Processing Guide - `/img` Command

## Overview

The `/img` command provides powerful image processing capabilities with Claude AI integration. It supports both general image analysis and a specialized **Code Fix Mode** for debugging and improving interfaces through screenshots.

## Basic Usage

### Starting an Image Session

```
/img [optional initial instruction]
```

**Examples:**
```
/img                           # Start session without instruction
/img Analyze this UI design    # Start with instruction
```

### Image Upload Process

1. **Send images** (up to 5 per batch)
   - Supported formats: PNG, JPG, JPEG, GIF, WebP
   - Max file size: 20MB per image
   - Can send one by one or all at once

2. **Add instructions** (optional)
   - Type any text to update processing instructions
   - Can be done before or after uploading images

3. **Process images**
   - Type `готово` / `done` / `process` to start analysis
   - Type `скасувати` / `cancel` to abort session

## 🔧 Code Fix Mode (NEW!)

### Activation

After uploading screenshots, type one of:
- `запит` (Ukrainian)
- `query` (English)
- `fix` (English)
- `фікс` (Ukrainian)

This activates **Code Fix Mode** where Claude can:
- Analyze interface problems from screenshots
- Explore your codebase automatically
- Implement fixes directly in source code
- Test changes if possible

### Code Fix Workflow

```
1. /img                    # Start session
2. [Upload screenshot]     # Send problem screenshot
3. запит                   # Activate fix mode
4. [Describe issue]        # Explain what's wrong
5. готово                  # Claude analyzes & fixes code
```

### What Claude Can Fix

**Interface Issues:**
- UI layout problems
- Button positioning and styling
- Text formatting and typography
- Color scheme inconsistencies
- Responsive design issues

**Code Issues:**
- Error messages and user experience
- Performance bottlenecks visible in UI
- Configuration problems
- API integration issues

**Supported Technologies:**
- Web apps (React, Vue, Angular, HTML/CSS)
- Backend APIs (Python, Node.js, PHP, Java)
- Mobile apps (Flutter, React Native)
- Desktop apps (Electron, Qt)
- Configuration files (Docker, CI/CD)

### Example Code Fix Session

```
User: /img
Bot:  📸 Image Processing Mode activated...

User: [uploads screenshot showing broken button layout]

User: запит
Bot:  🔧 Code Fix Mode Activated
      Please describe the issue...

User: The buttons are overlapping and text is cut off.
      This is a React component. Make them responsive.

User: готово
Bot:  [Analyzes screenshot, finds React components, fixes CSS]
      ✅ Fixed button layout in src/components/ButtonGroup.jsx
      ✅ Added responsive breakpoints
      ✅ Updated CSS Grid layout
```

## Regular Image Analysis

When not in Code Fix Mode, `/img` provides general image analysis:

**Capabilities:**
- Document and text analysis
- Design feedback and suggestions
- Technical diagram interpretation
- Code review from screenshots
- UI/UX analysis and recommendations

**Use Cases:**
- Design review and feedback
- Documentation from images
- Technical troubleshooting
- Learning and education
- Content creation assistance

## Session Management

### Commands During Session

| Command | Action | Aliases |
|---------|--------|---------|
| `готово` | Process images | `done`, `process` |
| `запит` | Enter Code Fix Mode | `query`, `fix`, `фікс` |
| `скасувати` | Cancel session | `cancel`, `відміна` |
| `[text]` | Update instructions | Any other text |

### Session Limits

- **Max images per session:** 5
- **Session timeout:** 5 minutes
- **Max file size:** 20MB per image
- **Supported formats:** PNG, JPG, JPEG, GIF, WebP

### Image Optimization

Images are automatically optimized:
- **Resolution:** Max 2048x2048 pixels
- **Quality:** 85% JPEG compression
- **Format conversion:** Automatic when beneficial

## Security & Privacy

### File Handling
- Images stored temporarily during processing
- Automatic cleanup after session ends
- Secure file validation and sanitization

### Code Access
- Code Fix Mode respects `APPROVED_DIRECTORY` settings
- Only files within approved directories can be modified
- All changes are logged for audit purposes

### Privacy
- Images processed locally within your system
- No images sent to external services (except Claude API)
- Full control over data retention

## Configuration

### Environment Variables

```bash
# Image processing settings
ENABLE_IMAGE_PROCESSING=true
IMAGE_MAX_FILE_SIZE=20971520          # 20MB
IMAGE_MAX_BATCH_SIZE=5
IMAGE_SESSION_TIMEOUT_MINUTES=5

# Image optimization
IMAGE_OPTIMIZATION_ENABLED=true
IMAGE_OPTIMIZATION_MAX_WIDTH=2048
IMAGE_OPTIMIZATION_MAX_HEIGHT=2048
IMAGE_OPTIMIZATION_QUALITY=85

# Claude integration
CLAUDE_SUPPORTS_IMAGES=true
CLAUDE_IMAGE_TIMEOUT_SECONDS=600
```

## Troubleshooting

### Common Issues

**"Image processing disabled"**
- Check `ENABLE_IMAGE_PROCESSING=true` in configuration

**"Session expired"**
- Sessions timeout after 5 minutes of inactivity
- Start a new session with `/img`

**"File too large"**
- Max file size is 20MB
- Reduce image resolution or compress before uploading

**"Claude CLI недоступний"**
- Check Claude CLI authentication
- Verify `CLAUDE_SUPPORTS_IMAGES=true`

### Debug Mode

Enable debug logging for detailed troubleshooting:
```bash
python -m src.main --debug
```

## Advanced Features

### Batch Processing
- Upload multiple images before processing
- Claude analyzes relationships between images
- Provides comprehensive multi-image insights

### Session Context
- Image sessions integrate with Claude conversation history
- Previous context influences analysis
- Cross-session learning and improvement

### Integration with Other Features
- Works with git integration for code changes
- Supports MCP contexts for enhanced analysis
- Integrates with session export functionality

## Best Practices

### For Code Fixes
1. **Clear screenshots** - Include full context of the problem
2. **Detailed descriptions** - Explain expected vs actual behavior
3. **Technology context** - Mention framework/language being used
4. **Specific requirements** - Include any constraints or preferences

### For General Analysis
1. **High-quality images** - Well-lit, clear, high resolution
2. **Focused shots** - Crop to relevant areas
3. **Multiple angles** - Different perspectives when helpful
4. **Context information** - Provide background in instructions

### Session Management
1. **Prepare images first** - Have all images ready before starting
2. **Clear instructions** - Be specific about what you want analyzed
3. **Single focus** - One analysis goal per session
4. **Timely processing** - Complete sessions within timeout window

## API Integration

### Custom Handlers
The image processing system is modular and extensible:

```python
# Custom image processor
class CustomImageProcessor(ImageProcessor):
    async def custom_analysis(self, images, context):
        # Your custom logic here
        pass
```

### Webhook Integration
Image processing events can trigger webhooks:
- Session started
- Image uploaded
- Processing complete
- Session ended

## Future Enhancements

### Planned Features
- Video processing support
- Real-time image streaming
- OCR and text extraction
- Image generation capabilities
- Advanced analytics and reporting

### Roadmap
- Q4 2024: Video support
- Q1 2025: Real-time streaming
- Q2 2025: Advanced OCR
- Q3 2025: Image generation

---

## Quick Reference

**Start session:** `/img [instruction]`
**Upload images:** Send image files (max 5, 20MB each)
**Code fix mode:** Type `запит` / `fix`
**Process:** Type `готово` / `done`
**Cancel:** Type `скасувати` / `cancel`

**Supported formats:** PNG, JPG, JPEG, GIF, WebP
**Session timeout:** 5 minutes
**Max batch size:** 5 images per session

For more help, type `/help` or visit the documentation.