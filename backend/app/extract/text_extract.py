"""
Plain text file extraction.
Handles .txt files and similar text-based documents.
"""
from pathlib import Path

from app.models.ir_models import DocumentIR, DocumentMetadata, TextBlock


def extract_text(
    file_bytes: bytes,
    filename: str,
    job_dir: Path | None = None,
) -> DocumentIR:
    """
    Extract content from a plain text file.
    
    Args:
        file_bytes: The raw file bytes
        filename: Original filename
        job_dir: Optional directory for saving extracted content
        
    Returns:
        DocumentIR with extracted content
    """
    # Try to decode the text with various encodings
    text_content = None
    encoding_used = "utf-8"
    
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            text_content = file_bytes.decode(encoding)
            encoding_used = encoding
            break
        except UnicodeDecodeError:
            continue
    
    if text_content is None:
        # Fallback: decode with replacement characters
        text_content = file_bytes.decode("utf-8", errors="replace")
    
    # Create metadata
    char_count = len(text_content)
    line_count = text_content.count('\n') + 1 if text_content else 0
    
    metadata = DocumentMetadata(
        filename=filename,
        mime_type="text/plain",
        page_count=1,  # Text files are considered single-page
        char_count=char_count,
        source_encoding=encoding_used,
    )
    
    # Create a single text block for the entire content
    blocks = []
    if text_content.strip():
        blocks.append(
            TextBlock(
                text=text_content,
                page_number=1,
            )
        )
    
    return DocumentIR(
        metadata=metadata,
        blocks=blocks,
    )
