"""
PDF document extraction using PyMuPDF.
Extracts text, tables, and renders pages as images for vision processing.
"""
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image

from app.models.ir_models import (
    DocumentIR,
    DocumentMetadata,
    TextBlock,
    TableBlock,
    ImageBlock,
    BlockLocation,
    TableCell,
)


def extract_pdf(
    file_bytes: bytes,
    filename: str,
    job_dir: Optional[Path] = None,
    render_pages_for_vision: bool = False,
    extract_embedded_images: bool = True,
) -> DocumentIR:
    """
    Extract content from a PDF file.
    
    Args:
        file_bytes: PDF file content
        filename: Original filename
        job_dir: Optional directory to save rendered page images
        render_pages_for_vision: Whether to render pages as images
        extract_embedded_images: Whether to extract embedded images from PDF
        
    Returns:
        DocumentIR with extracted content
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    
    try:
        blocks = []
        total_chars = 0
        page_char_counts = []
        
        for page_num, page in enumerate(doc, start=1):
            # Extract text
            text = page.get_text("text")
            char_count = len(text)
            page_char_counts.append(char_count)
            total_chars += char_count
            
            if text.strip():
                blocks.append(TextBlock(
                    content=text,
                    location=BlockLocation(page=page_num),
                    char_count=char_count,
                ))
            
            # Try to extract tables
            try:
                tables = page.find_tables()
                for table_idx, table in enumerate(tables):
                    table_block = _extract_table(table, page_num)
                    if table_block:
                        blocks.append(table_block)
            except Exception:
                # Table extraction can fail on some PDFs
                pass
            
            # Render page as image if requested
            if render_pages_for_vision and job_dir:
                image_block = _render_page_to_image(page, page_num, job_dir)
                if image_block:
                    blocks.append(image_block)
        
        # Extract embedded images if requested
        embedded_image_count = 0
        if extract_embedded_images and job_dir:
            embedded_images = _extract_embedded_images(doc, job_dir)
            blocks.extend(embedded_images)
            embedded_image_count = len(embedded_images)
        
        # Build metadata
        metadata = DocumentMetadata(
            filename=filename,
            file_type="pdf",
            mime_type="application/pdf",
            size_bytes=len(file_bytes),
            page_count=len(doc),
            total_chars=total_chars,
            total_images=embedded_image_count,
            pdf_title=doc.metadata.get("title") or None,
            pdf_author=doc.metadata.get("author") or None,
        )
        
        # Concatenate all text for full_text
        full_text = "\n\n".join(
            block.content for block in blocks 
            if isinstance(block, TextBlock)
        )
        
        return DocumentIR(
            metadata=metadata,
            blocks=blocks,
            full_text=full_text,
        )
    finally:
        doc.close()


def _extract_table(table, page_num: int) -> Optional[TableBlock]:
    """Extract a table from a PyMuPDF table object."""
    try:
        extracted = table.extract()
        if not extracted or len(extracted) == 0:
            return None
        
        rows = []
        for row_idx, row_data in enumerate(extracted):
            cells = []
            for cell_data in row_data:
                cell_text = str(cell_data) if cell_data else ""
                cells.append(TableCell(
                    content=cell_text,
                    is_header=(row_idx == 0),
                ))
            rows.append(cells)
        
        if rows:
            return TableBlock(
                rows=rows,
                location=BlockLocation(page=page_num),
            )
    except Exception:
        pass
    
    return None


def _render_page_to_image(
    page: fitz.Page,
    page_num: int,
    job_dir: Path,
    dpi: int = 150,
) -> Optional[ImageBlock]:
    """
    Render a PDF page to a JPEG image.
    
    Args:
        page: PyMuPDF page object
        page_num: Page number (1-indexed)
        job_dir: Directory to save the image
        dpi: Resolution for rendering
        
    Returns:
        ImageBlock with image metadata
    """
    try:
        # Render page to pixmap
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save as JPEG
        image_filename = f"page_{page_num:03d}.jpg"
        image_path = job_dir / image_filename
        img.save(image_path, "JPEG", quality=85)
        
        # Create ImageBlock
        return ImageBlock(
            image_id=f"page_{page_num}",
            image_path=str(image_path),
            mime_type="image/jpeg",
            width=pix.width,
            height=pix.height,
            location=BlockLocation(page=page_num),
        )
    except Exception as e:
        # Log error but don't fail extraction
        print(f"Failed to render page {page_num}: {e}")
        return None


def _extract_embedded_images(
    doc: fitz.Document,
    job_dir: Path,
    min_size: int = 50,
) -> list[ImageBlock]:
    """
    Extract embedded images from a PDF document.
    
    Args:
        doc: PyMuPDF document object
        job_dir: Directory to save extracted images
        min_size: Minimum width/height to consider (filters out tiny decorative images)
        
    Returns:
        List of ImageBlocks for extracted images
    """
    image_blocks = []
    seen_xrefs = set()  # Track already extracted images to avoid duplicates
    
    for page_num, page in enumerate(doc, start=1):
        try:
            # Get list of images on this page
            image_list = page.get_images(full=True)
            
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]  # Image xref number
                
                # Skip if we've already extracted this image
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                
                try:
                    # Extract image data
                    base_image = doc.extract_image(xref)
                    if not base_image:
                        continue
                    
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    
                    # Skip very small images (likely decorative)
                    if width < min_size or height < min_size:
                        continue
                    
                    # Determine MIME type
                    mime_map = {
                        "png": "image/png",
                        "jpeg": "image/jpeg",
                        "jpg": "image/jpeg",
                        "gif": "image/gif",
                        "webp": "image/webp",
                        "bmp": "image/bmp",
                    }
                    mime_type = mime_map.get(image_ext.lower(), "image/jpeg")
                    
                    # Save image to disk
                    image_id = f"embedded_p{page_num}_i{img_idx}"
                    image_filename = f"{image_id}.{image_ext}"
                    image_path = job_dir / image_filename
                    
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    
                    # Create ImageBlock
                    image_block = ImageBlock(
                        image_id=image_id,
                        image_path=str(image_path),
                        mime_type=mime_type,
                        width=width,
                        height=height,
                        location=BlockLocation(page=page_num),
                    )
                    image_blocks.append(image_block)
                    
                except Exception as e:
                    print(f"Failed to extract image {xref} from page {page_num}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Failed to get images from page {page_num}: {e}")
            continue
    
    return image_blocks


def get_page_char_counts(file_bytes: bytes) -> list[int]:
    """
    Get character counts for each page of a PDF.
    Used for vision gating decisions.
    
    Args:
        file_bytes: PDF file content
        
    Returns:
        List of character counts per page
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        counts = []
        for page in doc:
            text = page.get_text("text")
            counts.append(len(text))
        return counts
    finally:
        doc.close()


def render_specific_pages(
    file_bytes: bytes,
    page_numbers: list[int],
    job_dir: Path,
    dpi: int = 150,
) -> list[ImageBlock]:
    """
    Render specific pages as images for vision processing.
    
    Args:
        file_bytes: PDF file content
        page_numbers: List of page numbers to render (1-indexed)
        job_dir: Directory to save images
        dpi: Resolution for rendering
        
    Returns:
        List of ImageBlocks for rendered pages
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    image_blocks = []
    
    try:
        for page_num in page_numbers:
            if 1 <= page_num <= len(doc):
                page = doc[page_num - 1]  # 0-indexed
                image_block = _render_page_to_image(page, page_num, job_dir, dpi)
                if image_block:
                    image_blocks.append(image_block)
    finally:
        doc.close()
    
    return image_blocks
