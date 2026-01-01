"""
Vision gating logic.
Determines which pages/images need vision processing based on text coverage.
"""
from typing import Optional

from app.config import get_settings
from app.models.ir_models import DocumentIR, ImageBlock


def select_pages_for_vision(
    page_char_counts: list[int],
    min_chars_threshold: int = 100,
) -> list[int]:
    """
    Select PDF pages that need vision processing.
    Pages with low text coverage are candidates for OCR/vision.
    
    Args:
        page_char_counts: Character count per page
        min_chars_threshold: Minimum chars to consider a page "text-rich"
        
    Returns:
        List of page numbers (1-indexed) that need vision processing
    """
    settings = get_settings()
    
    # Find pages with low text coverage
    low_text_pages = [
        page_num + 1  # 1-indexed
        for page_num, char_count in enumerate(page_char_counts)
        if char_count < min_chars_threshold
    ]
    
    if not low_text_pages:
        return []
    
    # Calculate limits
    total_pages = len(page_char_counts)
    max_by_ratio = int(total_pages * settings.vision_page_ratio)
    max_pages = min(settings.max_vision_pages, max(1, max_by_ratio))
    
    # Return limited set of pages, prioritizing earlier pages
    return low_text_pages[:max_pages]


def select_images_for_vision(
    document_ir: DocumentIR,
    max_images: Optional[int] = None,
) -> list[ImageBlock]:
    """
    Select images from document that need vision processing.
    Deduplicates by hash and caps at configured limit.
    
    Args:
        document_ir: Document intermediate representation
        max_images: Maximum images to select (uses config default if None)
        
    Returns:
        List of ImageBlocks to process
    """
    settings = get_settings()
    limit = max_images or settings.max_vision_images
    
    # Get all image blocks
    image_blocks = document_ir.image_blocks
    
    if not image_blocks:
        return []
    
    # Deduplicate by hash
    seen_hashes = set()
    unique_images = []
    
    for img in image_blocks:
        img_hash = img.image_hash
        if img_hash and img_hash in seen_hashes:
            continue
        if img_hash:
            seen_hashes.add(img_hash)
        unique_images.append(img)
    
    # Return limited set
    return unique_images[:limit]


def should_use_vision(document_ir: DocumentIR) -> bool:
    """
    Determine if a document would benefit from vision processing.
    
    Returns True if:
    - Document is an image file
    - Document has embedded images
    - Document has pages with low text coverage
    """
    # Image files always need vision
    if document_ir.metadata.file_type == "image":
        return True
    
    # Check for embedded images
    if document_ir.image_blocks:
        return True
    
    # Check text coverage
    total_chars = document_ir.metadata.total_chars or 0
    page_count = document_ir.metadata.page_count or 1
    avg_chars_per_page = total_chars / page_count
    
    # Low average text suggests scanned document
    if avg_chars_per_page < 200:
        return True
    
    return False


def estimate_vision_cost(
    num_images: int,
    avg_tokens_per_image: int = 1000,
) -> dict:
    """
    Estimate token cost for vision processing.
    
    Args:
        num_images: Number of images to process
        avg_tokens_per_image: Average tokens per image (varies by size/detail)
        
    Returns:
        Dict with estimated costs
    """
    input_tokens = num_images * avg_tokens_per_image
    # Assume ~200 output tokens per image description
    output_tokens = num_images * 200
    
    return {
        "num_images": num_images,
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_total_tokens": input_tokens + output_tokens,
    }
