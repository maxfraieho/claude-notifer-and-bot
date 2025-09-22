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
try:
    from PIL import Image, ExifTags
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ExifTags = None
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

        # Check if PIL is available
        if not PIL_AVAILABLE:
            logger.warning("PIL/Pillow not available. Image processing features disabled.")
            self.enabled = False
        else:
            self.enabled = True

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

        # Use existing filename validation from SecurityValidator
        is_valid, error = self.security_validator.validate_filename(file_path.name)
        if not is_valid:
            raise SecurityError(f"Security validation failed: {error}")

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