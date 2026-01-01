"""
Hashing utilities for file and image deduplication.
"""
import hashlib
import io
from typing import Optional

from PIL import Image

# Try to import imagehash, fall back to simple hashing if not available
try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False


def compute_file_hash(data: bytes) -> str:
    """
    Compute MD5 hash of file data.
    
    Args:
        data: File bytes
        
    Returns:
        Hex digest of MD5 hash
    """
    return hashlib.md5(data).hexdigest()


def compute_image_hash(
    image_data: bytes,
    use_perceptual: bool = True,
) -> str:
    """
    Compute hash for an image for deduplication.
    
    Uses perceptual hashing (pHash) when available, which can detect
    similar images even with slight differences. Falls back to MD5.
    
    Args:
        image_data: Image file bytes
        use_perceptual: Whether to use perceptual hashing (if available)
        
    Returns:
        Hash string
    """
    if not use_perceptual or not IMAGEHASH_AVAILABLE:
        return compute_file_hash(image_data)
    
    try:
        img = Image.open(io.BytesIO(image_data))
        # Use pHash (perceptual hash) - robust to resize/compression
        phash = imagehash.phash(img)
        return str(phash)
    except Exception:
        # Fall back to MD5 on any error
        return compute_file_hash(image_data)


def images_are_similar(
    hash1: str,
    hash2: str,
    max_distance: int = 8,
) -> bool:
    """
    Check if two image hashes are similar.
    
    For perceptual hashes, compares Hamming distance.
    For MD5 hashes, requires exact match.
    
    Args:
        hash1: First image hash
        hash2: Second image hash
        max_distance: Maximum Hamming distance for similarity
        
    Returns:
        True if images are considered similar
    """
    if len(hash1) == 32 and len(hash2) == 32:
        # MD5 hashes - require exact match
        return hash1 == hash2
    
    if not IMAGEHASH_AVAILABLE:
        return hash1 == hash2
    
    try:
        # Parse as imagehash and compare
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        distance = h1 - h2
        return distance <= max_distance
    except Exception:
        return hash1 == hash2
