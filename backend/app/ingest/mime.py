"""
MIME type detection for uploaded files.
Uses magic numbers for reliable file type identification.
"""
import io
from typing import Literal

# Magic bytes for common file types
MAGIC_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"RIFF": "image/webp",  # WebP starts with RIFF, need to check for WEBP later
}


def detect_mime_type(file_bytes: bytes) -> str | None:
    """
    Detect MIME type from file bytes using magic signatures.
    
    Args:
        file_bytes: First few bytes of the file (at least 12 bytes recommended)
        
    Returns:
        MIME type string or None if unrecognized
    """
    if len(file_bytes) < 4:
        return None
    
    # Check PDF
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    
    # Check DOCX (ZIP-based Office format)
    if file_bytes[:4] == b"PK\x03\x04":
        # Need to check if it's actually a DOCX vs other Office formats
        # DOCX contains [Content_Types].xml with specific content
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    # Check JPEG
    if file_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    
    # Check PNG
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    
    # Check GIF
    if file_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    
    # Check WebP (RIFF....WEBP)
    if file_bytes[:4] == b"RIFF" and len(file_bytes) >= 12:
        if file_bytes[8:12] == b"WEBP":
            return "image/webp"
    
    # Check for plain text - if mostly printable ASCII characters
    # This is a heuristic check for text files
    try:
        # Try to decode as UTF-8
        sample = file_bytes[:1024].decode('utf-8', errors='strict')
        # Check if it's mostly printable text
        printable_ratio = sum(c.isprintable() or c in '\n\r\t' for c in sample) / len(sample)
        if printable_ratio > 0.9:
            return "text/plain"
    except (UnicodeDecodeError, ZeroDivisionError):
        pass
    
    return None


def get_file_category(mime_type: str) -> Literal["pdf", "docx", "image"] | None:
    """
    Get file category from MIME type.
    
    Args:
        mime_type: MIME type string
        
    Returns:
        Category string or None if not supported
    """
    mime_to_category = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "image/jpeg": "image",
        "image/png": "image",
        "image/gif": "image",
        "image/webp": "image",
        "text/plain": "text",
    }
    return mime_to_category.get(mime_type)


def validate_docx_mime(file_bytes: bytes) -> bool:
    """
    Additional validation to ensure a PK zip file is actually a DOCX.
    Checks for the presence of word/document.xml in the archive.
    
    Args:
        file_bytes: Complete file bytes
        
    Returns:
        True if valid DOCX, False otherwise
    """
    import zipfile
    
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zf:
            # DOCX files must contain word/document.xml
            return "word/document.xml" in zf.namelist()
    except (zipfile.BadZipFile, Exception):
        return False


def is_allowed_mime_type(mime_type: str | None) -> bool:
    """Check if the MIME type is in the allowed list."""
    allowed = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "text/plain",
    }
    return mime_type in allowed
