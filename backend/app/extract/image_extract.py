"""
Standalone image extraction.
Handles uploaded image files for vision-based analysis.
"""
import hashlib
import io
from pathlib import Path
from typing import Optional

from PIL import Image

from app.models.ir_models import (
    DocumentIR,
    DocumentMetadata,
    ImageBlock,
    BlockLocation,
)


def extract_image(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    job_dir: Optional[Path] = None,
) -> DocumentIR:
    """
    Extract content from an uploaded image file.
    Creates a single ImageBlock for vision processing.
    
    Args:
        file_bytes: Image file content
        filename: Original filename
        mime_type: Detected MIME type
        job_dir: Optional directory to save a copy
        
    Returns:
        DocumentIR with single ImageBlock
    """
    # Get image dimensions
    width, height = None, None
    try:
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size
        # Ensure image is in a supported format
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGB")
    except Exception as e:
        raise ValueError(f"Could not process image: {e}")
    
    # Calculate hash for identification
    image_hash = hashlib.md5(file_bytes).hexdigest()
    
    # Save copy if job_dir provided
    image_path = None
    if job_dir:
        ext = Path(filename).suffix.lower() or ".jpg"
        safe_filename = f"uploaded_image{ext}"
        image_path = job_dir / safe_filename
        image_path.write_bytes(file_bytes)
    
    # Create image block
    image_block = ImageBlock(
        image_id="uploaded_image",
        image_path=str(image_path) if image_path else None,
        image_data=file_bytes,
        mime_type=mime_type,
        width=width,
        height=height,
        location=BlockLocation(page=1),
        image_hash=image_hash,
    )
    
    # Build metadata
    metadata = DocumentMetadata(
        filename=filename,
        file_type="image",
        mime_type=mime_type,
        size_bytes=len(file_bytes),
        page_count=1,
        total_chars=0,
        total_images=1,
    )
    
    return DocumentIR(
        metadata=metadata,
        blocks=[image_block],
        full_text="",  # No text content for images (until vision processes it)
    )


def resize_for_vision(
    image_bytes: bytes,
    max_dimension: int = 2000,
    quality: int = 85,
) -> tuple[bytes, str]:
    """
    Resize image for vision API to reduce token usage.
    
    Args:
        image_bytes: Original image bytes
        max_dimension: Maximum width or height
        quality: JPEG quality (0-100)
        
    Returns:
        Tuple of (resized image bytes, mime type)
    """
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB if needed
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    
    # Resize if larger than max dimension
    width, height = img.size
    if width > max_dimension or height > max_dimension:
        ratio = min(max_dimension / width, max_dimension / height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Save as JPEG
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    
    return buffer.getvalue(), "image/jpeg"


def image_to_base64_data_url(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> str:
    """
    Convert image bytes to a base64 data URL for vision API.
    
    Args:
        image_bytes: Image content
        mime_type: MIME type of the image
        
    Returns:
        Data URL string (data:image/jpeg;base64,...)
    """
    import base64
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"
