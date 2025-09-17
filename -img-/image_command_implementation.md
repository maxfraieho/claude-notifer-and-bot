# Claude Code Telegram Bot - /img Command Implementation

## Overview
Complete implementation of image processing functionality for the Claude Code Telegram Bot.

## Components

### 1. Image Command Handler
```python

"""Main /img command handler for image processing.

Features:
- Multi-image upload support  
- Batch processing with Claude CLI
- Session management for image contexts
- Progress indicators and error handling
"""

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import structlog
from telegram import Update, Message
from telegram.ext import ContextTypes

from ...claude.facade import ClaudeIntegration
from ...config.settings import Settings
from ...exceptions import ClaudeError, SecurityError
from ...localization.util import t, get_user_id
from ..features.image_processor import ImageProcessor, ProcessedImage
from ..utils.error_handler import safe_user_error

logger = structlog.get_logger(__name__)

class ImageCommandHandler:
    """Handler for /img command and image processing workflow."""

    def __init__(self, settings: Settings, image_processor: ImageProcessor):
        """Initialize image command handler."""
        self.settings = settings
        self.image_processor = image_processor
        self.active_sessions: Dict[int, 'ImageSession'] = {}
        self.max_images_per_batch = settings.image_max_batch_size
        self.session_timeout = settings.image_session_timeout_minutes * 60

    async def handle_img_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /img command to start image processing session."""
        user_id = get_user_id(update)
        if not user_id:
            return

        logger.info("Starting image command session", user_id=user_id)

        # Extract initial instruction from command
        message_text = update.message.text or ""
        parts = message_text.split(maxsplit=1)
        initial_instruction = parts[1] if len(parts) > 1 else None

        # Create new image session
        session = ImageSession(
            user_id=user_id,
            initial_instruction=initial_instruction,
            timeout=self.session_timeout
        )
        self.active_sessions[user_id] = session

        # Send instruction message
        instruction_text = await self._get_instruction_message(context, user_id)
        await update.message.reply_text(
            instruction_text,
            parse_mode=None
        )

        # Set user state for image collection
        context.user_data['awaiting_images'] = True
        context.user_data['image_session_id'] = session.session_id

        # Schedule session cleanup
        asyncio.create_task(self._cleanup_session_after_timeout(user_id, session.session_id))

    async def handle_image_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle image uploads during an active session."""
        user_id = get_user_id(update)
        if not user_id or user_id not in self.active_sessions:
            return

        session = self.active_sessions[user_id]

        if not session.is_active():
            await self._cleanup_session(user_id)
            await update.message.reply_text("❌ Image session has expired. Use /img to start a new session.")
            return

        try:
            # Process the uploaded image
            photo = update.message.photo[-1] if update.message.photo else None
            if photo:
                processed_image = await self.image_processor.process_telegram_photo(
                    photo, 
                    update.message.caption,
                    user_id
                )
                session.add_image(processed_image)

                # Send confirmation
                await update.message.reply_text(
                    f"✅ Image {len(session.images)}/{self.max_images_per_batch} received. "
                    f"Send more images or type 'done' to process."
                )

                # Check if batch is full
                if len(session.images) >= self.max_images_per_batch:
                    await self._process_session_images(update, context, session)

        except Exception as e:
            logger.error("Error processing image upload", error=str(e), user_id=user_id)
            await safe_user_error(update, f"Error processing image: {str(e)}")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages during image session."""
        user_id = get_user_id(update)
        if not user_id or user_id not in self.active_sessions:
            return

        session = self.active_sessions[user_id]
        message_text = (update.message.text or "").strip().lower()

        if message_text in ['done', 'готово', 'процес', 'process']:
            if session.images:
                await self._process_session_images(update, context, session)
            else:
                await update.message.reply_text("❌ No images uploaded yet. Please send images first.")
        elif message_text in ['cancel', 'скасувати', 'відміна']:
            await self._cleanup_session(user_id)
            await update.message.reply_text("🚫 Image session cancelled.")
        else:
            # Update session instruction
            session.set_instruction(update.message.text)
            await update.message.reply_text(
                f"📝 Instruction updated. Current images: {len(session.images)}. "
                f"Send 'done' to process or continue uploading images."
            )

    async def _process_session_images(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        session: 'ImageSession'
    ) -> None:
        """Process all images in session with Claude CLI."""
        if not session.images:
            await update.message.reply_text("❌ No images to process.")
            return

        progress_msg = await update.message.reply_text(
            f"🔄 Processing {len(session.images)} image(s) with Claude..."
        )

        try:
            # Get Claude integration
            claude_integration = context.bot_data.get('claude_integration')
            if not claude_integration:
                await progress_msg.edit_text("❌ Claude integration not available.")
                return

            # Build prompt with image references
            prompt = self._build_claude_prompt(session)

            # Get current working directory
            current_dir = context.user_data.get(
                'current_directory', 
                self.settings.approved_directory
            )

            # Process with Claude
            claude_response = await claude_integration.run_command_with_images(
                prompt=prompt,
                images=session.images,
                working_directory=current_dir,
                user_id=session.user_id,
                session_id=context.user_data.get('claude_session_id')
            )

            # Update session ID
            context.user_data['claude_session_id'] = claude_response.session_id

            # Format and send response
            from ..utils.formatting import ResponseFormatter
            formatter = ResponseFormatter(self.settings)
            formatted_messages = formatter.format_claude_response(claude_response.content)

            # Delete progress message
            await progress_msg.delete()

            # Send responses
            for i, message in enumerate(formatted_messages):
                await update.message.reply_text(
                    message.text,
                    parse_mode=message.parse_mode,
                    reply_markup=message.reply_markup,
                    reply_to_message_id=update.message.message_id if i == 0 else None
                )

                if i < len(formatted_messages) - 1:
                    await asyncio.sleep(0.5)

        except Exception as e:
            logger.error("Error processing images with Claude", error=str(e))
            await progress_msg.edit_text(f"❌ Error processing images: {str(e)}")

        finally:
            # Clean up session
            await self._cleanup_session(session.user_id)

    def _build_claude_prompt(self, session: 'ImageSession') -> str:
        """Build Claude prompt with image context."""
        base_instruction = session.instruction or "Please analyze these images and provide insights."

        image_info = []
        for i, img in enumerate(session.images, 1):
            info = f"Image {i}: {img.filename}"
            if img.caption:
                info += f" (Caption: {img.caption})"
            image_info.append(info)

        prompt = f"""{base_instruction}

I'm providing you with {len(session.images)} image(s):
{chr(10).join(image_info)}

Please analyze these images and help me with the request above. Consider:
1. The content and context of each image
2. Any text or UI elements visible
3. Technical aspects if relevant (code, diagrams, etc.)
4. Relationships between images if multiple
5. Specific actionable recommendations
"""

        return prompt

    async def _get_instruction_message(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
        """Get localized instruction message."""
        try:
            return await t(context, user_id, "commands.img.instructions")
        except:
            return (
                "📸 **Image Processing Mode**\n\n"
                f"Please send your images (up to {self.max_images_per_batch} files). "
                "You can send them one by one or all at once.\n\n"
                "**Supported formats:** PNG, JPG, JPEG, GIF, WebP\n"
                "**Max file size:** 20MB per image\n\n"
                "After uploading, type your instructions or 'done' to process.\n\n"
                "Type 'cancel' to stop."
            )

    async def _cleanup_session(self, user_id: int) -> None:
        """Clean up user's image session."""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            await session.cleanup()
            del self.active_sessions[user_id]
            logger.info("Cleaned up image session", user_id=user_id)

    async def _cleanup_session_after_timeout(self, user_id: int, session_id: str) -> None:
        """Clean up session after timeout."""
        await asyncio.sleep(self.session_timeout)

        if (user_id in self.active_sessions and 
            self.active_sessions[user_id].session_id == session_id):
            await self._cleanup_session(user_id)


class ImageSession:
    """Represents an active image processing session."""

    def __init__(self, user_id: int, initial_instruction: Optional[str] = None, timeout: int = 300):
        """Initialize image session."""
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.instruction = initial_instruction
        self.images: List[ProcessedImage] = []
        self.created_at = asyncio.get_event_loop().time()
        self.timeout = timeout

    def add_image(self, image: ProcessedImage) -> None:
        """Add processed image to session."""
        self.images.append(image)

    def set_instruction(self, instruction: str) -> None:
        """Set or update instruction."""
        self.instruction = instruction

    def is_active(self) -> bool:
        """Check if session is still active."""
        return (asyncio.get_event_loop().time() - self.created_at) < self.timeout

    async def cleanup(self) -> None:
        """Clean up session resources."""
        for image in self.images:
            await image.cleanup()
        self.images.clear()

```

### 2. Image Processor
```python

"""Image processing logic for Claude Code Telegram Bot.

Features:
- Image validation and preprocessing
- Format conversion and optimization  
- Metadata extraction
- Base64 encoding for Claude CLI
- Temporary file management
"""

import asyncio
import base64
import hashlib
import mimetypes
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import structlog
from telegram import PhotoSize
from PIL import Image, ExifTags
import aiofiles

from ...config.settings import Settings
from ...exceptions import SecurityError
from ...security.validators import SecurityValidator

logger = structlog.get_logger(__name__)

@dataclass
class ProcessedImage:
    """Processed image data with metadata."""

    filename: str
    file_path: Path
    file_size: int
    format: str
    dimensions: Tuple[int, int]
    base64_data: Optional[str] = None
    caption: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    temp_file: bool = True

    def __post_init__(self):
        """Initialize after creation."""
        self.file_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate SHA-256 hash of file."""
        hash_obj = hashlib.sha256()
        try:
            with open(self.file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception:
            return ""

    async def get_base64_data(self) -> str:
        """Get base64 encoded image data."""
        if not self.base64_data:
            async with aiofiles.open(self.file_path, 'rb') as f:
                image_data = await f.read()
                self.base64_data = base64.b64encode(image_data).decode('utf-8')
        return self.base64_data

    async def cleanup(self) -> None:
        """Clean up temporary files."""
        if self.temp_file and self.file_path.exists():
            try:
                self.file_path.unlink()
                logger.debug("Cleaned up temp image file", path=str(self.file_path))
            except Exception as e:
                logger.warning("Failed to cleanup temp file", error=str(e))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "filename": self.filename,
            "file_size": self.file_size,
            "format": self.format,
            "dimensions": self.dimensions,
            "caption": self.caption,
            "metadata": self.metadata,
            "file_hash": self.file_hash
        }


class ImageProcessor:
    """Process and validate images for Claude CLI integration."""

    def __init__(self, settings: Settings, security_validator: SecurityValidator):
        """Initialize image processor."""
        self.settings = settings
        self.security_validator = security_validator
        self.temp_dir = Path(settings.image_temp_directory)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Supported image formats
        self.supported_formats = {
            'PNG': '.png',
            'JPEG': '.jpg', 
            'GIF': '.gif',
            'WEBP': '.webp',
            'BMP': '.bmp',
            'TIFF': '.tiff'
        }

        # MIME type mapping
        self.mime_mapping = {
            'image/png': 'PNG',
            'image/jpeg': 'JPEG',
            'image/jpg': 'JPEG',
            'image/gif': 'GIF',
            'image/webp': 'WEBP',
            'image/bmp': 'BMP',
            'image/tiff': 'TIFF',
            'image/tif': 'TIFF'
        }

    async def process_telegram_photo(
        self, 
        photo: PhotoSize, 
        caption: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> ProcessedImage:
        """Process image from Telegram PhotoSize."""
        logger.info("Processing Telegram photo", 
                   file_id=photo.file_id, 
                   size=photo.file_size,
                   user_id=user_id)

        # Download image from Telegram
        file = await photo.get_file()
        temp_path = self.temp_dir / f"tg_{photo.file_id}_{photo.file_unique_id}.jpg"

        try:
            await file.download_to_drive(str(temp_path))

            # Process the downloaded image
            return await self.process_image_file(
                temp_path,
                caption=caption,
                original_filename=f"telegram_photo_{photo.file_unique_id}.jpg"
            )

        except Exception as e:
            # Clean up temp file if processing failed
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

    async def process_image_file(
        self, 
        file_path: Path, 
        caption: Optional[str] = None,
        original_filename: Optional[str] = None
    ) -> ProcessedImage:
        """Process image file from path."""
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        logger.info("Processing image file", path=str(file_path))

        # Validate file security
        await self._validate_image_security(file_path)

        # Get image info
        img_info = await self._extract_image_info(file_path)

        # Validate image properties
        await self._validate_image_properties(img_info)

        # Optimize image if needed
        optimized_path = await self._optimize_image(file_path, img_info)

        return ProcessedImage(
            filename=original_filename or file_path.name,
            file_path=optimized_path,
            file_size=optimized_path.stat().st_size,
            format=img_info['format'],
            dimensions=img_info['dimensions'],
            caption=caption,
            metadata=img_info['metadata'],
            temp_file=True
        )

    async def _validate_image_security(self, file_path: Path) -> None:
        """Validate image for security issues."""
        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.settings.image_max_file_size:
            raise SecurityError(
                f"Image file too large: {file_size / (1024*1024):.1f}MB "
                f"(max: {self.settings.image_max_file_size / (1024*1024):.1f}MB)"
            )

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type not in self.mime_mapping:
            raise SecurityError(f"Unsupported image format: {mime_type}")

        # Additional security validation through SecurityValidator
        try:
            await asyncio.to_thread(
                self.security_validator.validate_file_content, 
                file_path
            )
        except Exception as e:
            raise SecurityError(f"Security validation failed: {e}")

    async def _extract_image_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract image information and metadata."""
        def _extract_sync():
            with Image.open(file_path) as img:
                # Basic info
                info = {
                    'format': img.format,
                    'mode': img.mode,
                    'dimensions': img.size,
                    'metadata': {}
                }

                # Extract EXIF data
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        exif_dict = {}
                        for tag, value in exif.items():
                            tag_name = ExifTags.TAGS.get(tag, str(tag))
                            exif_dict[tag_name] = str(value) if not isinstance(value, (int, float, str)) else value
                        info['metadata']['exif'] = exif_dict

                # Get color info
                if hasattr(img, 'getcolors'):
                    try:
                        colors = img.getcolors(maxcolors=256*256*256)
                        if colors:
                            info['metadata']['color_count'] = len(colors)
                            info['metadata']['dominant_color'] = colors[0][1] if colors else None
                    except Exception:
                        pass

                return info

        return await asyncio.to_thread(_extract_sync)

    async def _validate_image_properties(self, img_info: Dict[str, Any]) -> None:
        """Validate image properties."""
        dimensions = img_info['dimensions']
        width, height = dimensions

        # Check dimensions
        if width > self.settings.image_max_width or height > self.settings.image_max_height:
            raise SecurityError(
                f"Image dimensions too large: {width}x{height} "
                f"(max: {self.settings.image_max_width}x{self.settings.image_max_height})"
            )

        # Check minimum dimensions
        if width < self.settings.image_min_width or height < self.settings.image_min_height:
            raise SecurityError(
                f"Image dimensions too small: {width}x{height} "
                f"(min: {self.settings.image_min_width}x{self.settings.image_min_height})"
            )

        # Validate format
        if img_info['format'] not in self.supported_formats:
            raise SecurityError(f"Unsupported image format: {img_info['format']}")

    async def _optimize_image(self, file_path: Path, img_info: Dict[str, Any]) -> Path:
        """Optimize image for Claude CLI processing."""
        def _optimize_sync():
            with Image.open(file_path) as img:
                # Convert to RGB if needed (for JPEG compatibility)
                if img.mode not in ('RGB', 'RGBA'):
                    if img.mode == 'P' and 'transparency' in img.info:
                        img = img.convert('RGBA')
                    else:
                        img = img.convert('RGB')

                # Resize if too large
                width, height = img.size
                max_size = (self.settings.image_optimization_max_width, 
                           self.settings.image_optimization_max_height)

                if width > max_size[0] or height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    logger.info("Resized image for optimization", 
                               original_size=f"{width}x{height}",
                               new_size=f"{img.width}x{img.height}")

                # Save optimized version
                optimized_path = self.temp_dir / f"opt_{file_path.stem}.jpg"

                # Save with optimization
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': self.settings.image_optimization_quality,
                    'optimize': True
                }

                # Handle transparency for RGBA images
                if img.mode == 'RGBA':
                    # Create white background for JPEG
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if len(img.split()) == 4 else None)
                    img = background

                img.save(optimized_path, **save_kwargs)
                return optimized_path

        return await asyncio.to_thread(_optimize_sync)

    async def batch_process_images(
        self, 
        image_files: List[Path],
        captions: Optional[List[str]] = None
    ) -> List[ProcessedImage]:
        """Process multiple images in batch."""
        if len(image_files) > self.settings.image_max_batch_size:
            raise SecurityError(
                f"Too many images in batch: {len(image_files)} "
                f"(max: {self.settings.image_max_batch_size})"
            )

        results = []
        captions = captions or [None] * len(image_files)

        # Process images concurrently
        tasks = []
        for i, (image_file, caption) in enumerate(zip(image_files, captions)):
            task = asyncio.create_task(
                self.process_image_file(image_file, caption=caption),
                name=f"process_image_{i}"
            )
            tasks.append(task)

        # Wait for all processing to complete
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for exceptions
            processed_images = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to process image {i}", error=str(result))
                    raise result
                processed_images.append(result)

            return processed_images

        except Exception as e:
            # Clean up any successfully processed images
            for result in results:
                if isinstance(result, ProcessedImage):
                    await result.cleanup()
            raise

    async def create_image_summary(self, images: List[ProcessedImage]) -> Dict[str, Any]:
        """Create summary of processed images."""
        if not images:
            return {}

        total_size = sum(img.file_size for img in images)
        formats = list(set(img.format for img in images))
        dimensions = [img.dimensions for img in images]

        return {
            'count': len(images),
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'formats': formats,
            'dimensions': dimensions,
            'has_captions': sum(1 for img in images if img.caption),
            'average_size': total_size // len(images) if images else 0
        }

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """Clean up old temporary files."""
        import time

        if not self.temp_dir.exists():
            return 0

        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0

        for file_path in self.temp_dir.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning("Failed to cleanup old temp file", 
                                 path=str(file_path), error=str(e))

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old temp files")

        return cleaned_count

```

### 3. Claude Image Integration
```python

"""Claude CLI integration for image processing.

Features:
- Image attachment via command line
- Base64 encoding for CLI input
- Session management with image context
- Error handling for image processing
"""

import asyncio
import json
import shlex
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import structlog

from ...config.settings import Settings
from ...exceptions import ClaudeError, ClaudeTimeoutError
from ..features.image_processor import ProcessedImage

logger = structlog.get_logger(__name__)

class ClaudeImageIntegration:
    """Handle image processing with Claude CLI."""

    def __init__(self, settings: Settings):
        """Initialize Claude image integration."""
        self.settings = settings
        self.claude_cli_path = settings.claude_cli_path or 'claude'

    async def process_images_with_claude(
        self,
        prompt: str,
        images: List[ProcessedImage], 
        working_directory: Path,
        session_id: Optional[str] = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """Process images with Claude CLI."""
        if not images:
            raise ClaudeError("No images provided for processing")

        logger.info("Processing images with Claude CLI", 
                   image_count=len(images),
                   session_id=session_id)

        timeout = timeout or self.settings.claude_timeout_seconds

        try:
            # Prepare command with image attachments
            cmd_args = await self._build_claude_command(prompt, images, session_id)

            # Execute Claude CLI with images
            result = await self._execute_claude_command(
                cmd_args,
                working_directory,
                timeout
            )

            return {
                'success': True,
                'content': result['stdout'],
                'session_id': result.get('session_id', session_id),
                'cost': result.get('cost', 0.0),
                'duration_ms': result.get('duration_ms', 0),
                'images_processed': len(images)
            }

        except asyncio.TimeoutError:
            raise ClaudeTimeoutError(
                f"Claude CLI timed out after {timeout} seconds while processing {len(images)} images"
            )
        except Exception as e:
            logger.error("Claude CLI execution failed", error=str(e))
            raise ClaudeError(f"Claude CLI failed: {e}")

    async def _build_claude_command(
        self, 
        prompt: str, 
        images: List[ProcessedImage],
        session_id: Optional[str] = None
    ) -> List[str]:
        """Build Claude CLI command with image attachments."""
        cmd_args = [self.claude_cli_path]

        # Add session continuation if provided
        if session_id:
            cmd_args.extend(['--continue', session_id])

        # Add model specification
        if self.settings.claude_model:
            cmd_args.extend(['--model', self.settings.claude_model])

        # Add timeout
        cmd_args.extend(['--timeout', str(self.settings.claude_timeout_seconds)])

        # Method 1: Using file paths (preferred for Claude CLI)
        if self._supports_file_attachments():
            for image in images:
                cmd_args.extend(['--attach', str(image.file_path)])

        # Method 2: Using base64 input (fallback)
        else:
            # Create a temporary file with combined prompt and image data
            temp_input = await self._create_temp_input_file(prompt, images)
            cmd_args.extend(['--input', str(temp_input)])
            return cmd_args

        # Add the text prompt
        cmd_args.append(prompt)

        return cmd_args

    async def _create_temp_input_file(
        self, 
        prompt: str, 
        images: List[ProcessedImage]
    ) -> Path:
        """Create temporary input file with prompt and base64 image data."""
        temp_file = Path(tempfile.mktemp(suffix='.json', prefix='claude_img_'))

        # Prepare image data
        image_data = []
        for i, image in enumerate(images):
            base64_data = await image.get_base64_data()
            image_data.append({
                'type': 'image',
                'source': {
                    'type': 'base64',
                    'media_type': f'image/{image.format.lower()}',
                    'data': base64_data
                },
                'filename': image.filename,
                'caption': image.caption
            })

        # Create input structure
        input_data = {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt}
                    ] + image_data
                }
            ]
        }

        # Write to temp file
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(input_data, f, indent=2)

        logger.debug("Created temp input file", path=str(temp_file))
        return temp_file

    def _supports_file_attachments(self) -> bool:
        """Check if Claude CLI supports file attachments."""
        # This would normally check Claude CLI version/capabilities
        # For now, assume it supports file attachments
        return True

    async def _execute_claude_command(
        self,
        cmd_args: List[str],
        working_directory: Path,
        timeout: int
    ) -> Dict[str, Any]:
        """Execute Claude CLI command and parse response."""
        logger.debug("Executing Claude CLI command", 
                    cmd=shlex.join(cmd_args),
                    cwd=str(working_directory))

        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_directory
        )

        try:
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')

            # Check return code
            if process.returncode != 0:
                error_msg = f"Claude CLI failed with exit code {process.returncode}"
                if stderr_text:
                    error_msg += f": {stderr_text}"
                raise ClaudeError(error_msg)

            # Parse Claude CLI output for metadata
            result = {
                'stdout': stdout_text,
                'stderr': stderr_text,
                'return_code': process.returncode
            }

            # Try to extract session ID from output
            session_id = self._extract_session_id(stdout_text)
            if session_id:
                result['session_id'] = session_id

            # Try to extract cost information
            cost = self._extract_cost_info(stdout_text)
            if cost:
                result['cost'] = cost

            return result

        except asyncio.TimeoutError:
            # Kill the process
            try:
                process.kill()
                await process.wait()
            except:
                pass
            raise

    def _extract_session_id(self, output: str) -> Optional[str]:
        """Extract session ID from Claude CLI output."""
        # Look for session ID patterns in output
        import re

        patterns = [
            r'Session ID: ([a-zA-Z0-9-]+)',
            r'session_id["']\s*:\s*["'']([^"']+)["'']',
            r'--continue\s+([a-zA-Z0-9-]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)

        return None

    def _extract_cost_info(self, output: str) -> Optional[float]:
        """Extract cost information from Claude CLI output."""
        import re

        patterns = [
            r'Cost: \$([0-9.]+)',
            r'cost["']\s*:\s*([0-9.]+)',
            r'Total cost: \$([0-9.]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return None

    async def get_claude_cli_info(self) -> Dict[str, Any]:
        """Get Claude CLI version and capability information."""
        try:
            # Get version info
            process = await asyncio.create_subprocess_exec(
                self.claude_cli_path, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=10
            )

            version_info = stdout.decode('utf-8', errors='replace').strip()

            # Get help info to check for image support
            process = await asyncio.create_subprocess_exec(
                self.claude_cli_path, '--help',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=10
            )

            help_text = stdout.decode('utf-8', errors='replace')

            return {
                'version': version_info,
                'supports_file_attachments': '--attach' in help_text,
                'supports_input_files': '--input' in help_text,
                'supports_images': any(word in help_text.lower() 
                                     for word in ['image', 'photo', 'picture']),
                'help_text': help_text
            }

        except Exception as e:
            logger.error("Failed to get Claude CLI info", error=str(e))
            return {
                'version': 'unknown',
                'supports_file_attachments': False,
                'supports_input_files': False,
                'supports_images': False,
                'error': str(e)
            }

```

### 4. Configuration Updates
```python

"""Configuration updates for image processing functionality."""

# Add these fields to settings.py in the Settings class:

# Image processing settings
enable_image_processing: bool = Field(True, description="Enable image upload and processing")
image_max_file_size: int = Field(20 * 1024 * 1024, description="Max image file size in bytes (20MB)")
image_max_batch_size: int = Field(5, description="Max images per batch processing")
image_session_timeout_minutes: int = Field(5, description="Image session timeout in minutes")
image_temp_directory: Path = Field(default=Path("/tmp/claude_bot_images"), description="Temp directory for images")

# Image validation settings
image_max_width: int = Field(4096, description="Maximum image width in pixels")
image_max_height: int = Field(4096, description="Maximum image height in pixels") 
image_min_width: int = Field(32, description="Minimum image width in pixels")
image_min_height: int = Field(32, description="Minimum image height in pixels")

# Image optimization settings
image_optimization_enabled: bool = Field(True, description="Enable image optimization")
image_optimization_max_width: int = Field(2048, description="Max width for optimization")
image_optimization_max_height: int = Field(2048, description="Max height for optimization")
image_optimization_quality: int = Field(85, description="JPEG quality for optimization (1-100)")

# Claude image integration settings
claude_supports_images: bool = Field(True, description="Whether Claude CLI supports images")
claude_image_timeout_seconds: int = Field(600, description="Timeout for image processing with Claude")

```

### 5. Database Schema
```sql

"""Database schema updates for image processing."""

# Add this migration to database.py:

IMAGE_SCHEMA_MIGRATION = '''
-- Images metadata table
CREATE TABLE image_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id TEXT,
    message_id INTEGER,
    filename TEXT NOT NULL,
    original_filename TEXT,
    file_size INTEGER NOT NULL,
    format TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    caption TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    processing_status TEXT DEFAULT 'uploaded', -- uploaded, processing, completed, failed
    processing_error TEXT,
    metadata JSON,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (message_id) REFERENCES messages(message_id)
);

-- Image processing sessions table  
CREATE TABLE image_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    instruction TEXT,
    status TEXT DEFAULT 'active', -- active, processing, completed, cancelled, expired
    images_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Indexes for performance
CREATE INDEX idx_image_uploads_user_id ON image_uploads(user_id);
CREATE INDEX idx_image_uploads_session_id ON image_uploads(session_id);  
CREATE INDEX idx_image_uploads_hash ON image_uploads(file_hash);
CREATE INDEX idx_image_sessions_user_id ON image_sessions(user_id);
CREATE INDEX idx_image_sessions_status ON image_sessions(status);
CREATE INDEX idx_image_sessions_expires_at ON image_sessions(expires_at);
'''

```

### 6. Repository Updates
```python

"""Repository updates for image processing."""

class ImageRepository:
    """Image data access layer."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def save_image_upload(self, image_data: dict) -> int:
        """Save image upload record."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                '''
                INSERT INTO image_uploads 
                (user_id, session_id, message_id, filename, original_filename, 
                 file_size, format, width, height, file_hash, caption, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    image_data['user_id'], image_data.get('session_id'),
                    image_data.get('message_id'), image_data['filename'],
                    image_data.get('original_filename'), image_data['file_size'],
                    image_data['format'], image_data['width'], image_data['height'],
                    image_data['file_hash'], image_data.get('caption'),
                    json.dumps(image_data.get('metadata', {}))
                )
            )
            await conn.commit()
            return cursor.lastrowid

    async def create_image_session(self, session_data: dict) -> str:
        """Create new image processing session."""
        async with self.db.get_connection() as conn:
            await conn.execute(
                '''
                INSERT INTO image_sessions 
                (session_id, user_id, instruction, expires_at)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    session_data['session_id'], session_data['user_id'],
                    session_data.get('instruction'), session_data.get('expires_at')
                )
            )
            await conn.commit()
            return session_data['session_id']

    async def update_image_session(self, session_id: str, updates: dict):
        """Update image session."""
        set_clauses = []
        params = []

        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return

        params.append(session_id)

        async with self.db.get_connection() as conn:
            await conn.execute(
                f'''
                UPDATE image_sessions 
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                ''',
                params
            )
            await conn.commit()

    async def get_user_image_stats(self, user_id: int, days: int = 30) -> dict:
        """Get user image processing statistics."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                '''
                SELECT 
                    COUNT(*) as total_images,
                    SUM(file_size) as total_size,
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as successful,
                    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed
                FROM image_uploads 
                WHERE user_id = ? AND uploaded_at > datetime('now', '-' || ? || ' days')
                ''',
                (user_id, days)
            )
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired image sessions."""
        async with self.db.get_connection() as conn:
            cursor = await conn.execute(
                '''
                UPDATE image_sessions 
                SET status = 'expired' 
                WHERE status = 'active' AND expires_at < CURRENT_TIMESTAMP
                '''
            )
            await conn.commit()
            return cursor.rowcount

```

### 7. Localization Updates
```python

"""Localization updates for image processing."""

# Add to localization/translations/en.json:
en_translations = {
    "commands": {
        "img": {
            "title": "Image Processing",
            "description": "Process images with Claude AI",
            "instructions": "📸 **Image Processing Mode**\n\nPlease send your images (up to {max_images} files). You can send them one by one or all at once.\n\n**Supported formats:** PNG, JPG, JPEG, GIF, WebP\n**Max file size:** {max_size}MB per image\n\nAfter uploading, type your instructions or 'done' to process.\n\nType 'cancel' to stop.",
            "session_expired": "❌ Image session has expired. Use /img to start a new session.",
            "image_received": "✅ Image {current}/{max} received. Send more images or type 'done' to process.",
            "no_images": "❌ No images uploaded yet. Please send images first.",
            "cancelled": "🚫 Image session cancelled.",
            "instruction_updated": "📝 Instruction updated. Current images: {count}. Send 'done' to process or continue uploading images.",
            "processing": "🔄 Processing {count} image(s) with Claude...",
            "error": "❌ Error processing images: {error}"
        }
    }
}

# Add to localization/translations/uk.json:
uk_translations = {
    "commands": {
        "img": {
            "title": "Обробка Зображень",
            "description": "Обробка зображень за допомогою Claude AI",
            "instructions": "📸 **Режим Обробки Зображень**\n\nБудь ласка, надішліть ваші зображення (до {max_images} файлів). Ви можете надсилати їх по одному або всі відразу.\n\n**Підтримувані формати:** PNG, JPG, JPEG, GIF, WebP\n**Макс. розмір файлу:** {max_size}МБ на зображення\n\nПісля завантаження введіть інструкції або 'готово' для обробки.\n\nНадрукуйте 'скасувати' для зупинки.",
            "session_expired": "❌ Сесія обробки зображень закінчилася. Використайте /img для початку нової сесії.",
            "image_received": "✅ Зображення {current}/{max} отримано. Надішліть більше зображень або наберіть 'готово' для обробки.",
            "no_images": "❌ Зображення ще не завантажені. Спочатку надішліть зображення.",
            "cancelled": "🚫 Сесія обробки зображень скасована.",
            "instruction_updated": "📝 Інструкція оновлена. Поточна кількість зображень: {count}. Надішліть 'готово' для обробки або продовжуйте завантажувати зображення.",
            "processing": "🔄 Обробка {count} зображення(ень) за допомогою Claude...",
            "error": "❌ Помилка обробки зображень: {error}"
        }
    }
}

```

## Integration Guide
```python

"""Integration guide for /img command implementation."""

# STEP 1: Install Dependencies
# Add to requirements.txt or install manually:
# pip install Pillow aiofiles

# STEP 2: Update Configuration
# 1. Add image settings to config/settings.py (see config_updates above)
# 2. Add environment variables to .env:
#    IMAGE_MAX_FILE_SIZE=20971520
#    IMAGE_MAX_BATCH_SIZE=5
#    IMAGE_SESSION_TIMEOUT_MINUTES=5
#    IMAGE_TEMP_DIRECTORY=/tmp/claude_bot_images

# STEP 3: Database Migration
# 1. Add image schema migration to storage/database.py
# 2. Update migration list in _get_migrations() method
# 3. Add ImageRepository to storage/repositories.py

# STEP 4: Create New Files
# 1. Create bot/handlers/image_command.py
# 2. Create bot/features/image_processor.py  
# 3. Create claude/image_integration.py
# 4. Add ImageRepository to storage/repositories.py

# STEP 5: Update Existing Files

# bot/core.py - Add image command handler:
def _register_handlers(self):
    # ... existing handlers ...

    # Add image command
    if self.settings.enable_image_processing:
        from .handlers.image_command import ImageCommandHandler
        from .features.image_processor import ImageProcessor

        image_processor = ImageProcessor(self.settings, self.deps['security_validator'])
        image_handler = ImageCommandHandler(self.settings, image_processor)

        self.app.add_handler(CommandHandler('img', self._inject_deps(image_handler.handle_img_command)))

        # Update existing photo handler to check for active image sessions
        # Modify handle_photo in handlers/message.py

# bot/handlers/message.py - Update handle_photo:
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if user has active image session
    if context.user_data.get('awaiting_images'):
        image_handler = context.bot_data.get('image_handler')
        if image_handler:
            await image_handler.handle_image_upload(update, context)
            return

    # ... existing photo handling code ...

# STEP 6: Update Claude Integration
# Modify claude/facade.py or integration.py to support images:

async def run_command_with_images(
    self,
    prompt: str,
    images: List[ProcessedImage],
    working_directory: Path,
    user_id: int,
    session_id: Optional[str] = None
) -> ClaudeResponse:
    """Run Claude command with image attachments."""

    if not self.image_integration:
        from .image_integration import ClaudeImageIntegration
        self.image_integration = ClaudeImageIntegration(self.config)

    result = await self.image_integration.process_images_with_claude(
        prompt=prompt,
        images=images,
        working_directory=working_directory,
        session_id=session_id,
        timeout=self.config.claude_image_timeout_seconds
    )

    return ClaudeResponse(
        content=result['content'],
        session_id=result['session_id'],
        cost=result['cost'],
        duration_ms=result['duration_ms'],
        is_error=not result['success']
    )

# STEP 7: Update Bot Command Menu
# Add to bot/core.py in _set_bot_commands():
BotCommand("img", "Process images with Claude AI")

# STEP 8: Add Localization
# Update localization files with image-related translations

# STEP 9: Add Feature Flag
# Update config/features.py:
@property
def image_processing_enabled(self) -> bool:
    return self.settings.enable_image_processing

# STEP 10: Testing
# 1. Test image upload and validation
# 2. Test batch processing
# 3. Test session timeout
# 4. Test Claude CLI integration
# 5. Test error handling

```

