"""
Document Intermediate Representation (IR) models.
Provides a unified structure for extracted document content across all file types.
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BlockType(str, Enum):
    """Types of content blocks in a document."""
    TEXT = "text"
    TABLE = "table"
    FORM = "form"
    IMAGE = "image"


class BlockLocation(BaseModel):
    """Location information for a content block."""
    page: int | None = Field(default=None, ge=1, description="Page number (1-indexed)")
    paragraph_index: int | None = Field(default=None, ge=0, description="Paragraph index in DOCX")
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description="Bounding box (x0, y0, x1, y1) in normalized coordinates"
    )


class TextBlock(BaseModel):
    """A block of text content."""
    block_type: BlockType = Field(default=BlockType.TEXT)
    content: str = Field(..., description="Text content")
    location: BlockLocation = Field(default_factory=BlockLocation)
    style: dict[str, Any] = Field(
        default_factory=dict,
        description="Style information (font, size, bold, etc.)"
    )
    char_count: int = Field(default=0, ge=0, description="Character count")
    
    def model_post_init(self, _context: Any) -> None:
        """Set char_count from content if not provided."""
        if not self.char_count:
            object.__setattr__(self, "char_count", len(self.content))


class TableCell(BaseModel):
    """A cell in a table."""
    content: str = Field(default="", description="Cell text content")
    row_span: int = Field(default=1, ge=1)
    col_span: int = Field(default=1, ge=1)
    is_header: bool = Field(default=False)


class TableBlock(BaseModel):
    """A table content block."""
    block_type: BlockType = Field(default=BlockType.TABLE)
    rows: list[list[TableCell]] = Field(default_factory=list, description="Table rows")
    location: BlockLocation = Field(default_factory=BlockLocation)
    caption: str | None = Field(default=None, description="Table caption if available")
    
    @property
    def row_count(self) -> int:
        return len(self.rows)
    
    @property
    def col_count(self) -> int:
        return max((len(row) for row in self.rows), default=0)
    
    def to_markdown(self) -> str:
        """Convert table to markdown format."""
        if not self.rows:
            return ""
        
        lines = []
        for i, row in enumerate(self.rows):
            cells = [cell.content.replace("|", "\\|") for cell in row]
            lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                # Add header separator
                lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
        
        return "\n".join(lines)


class FormField(BaseModel):
    """A form field with key-value pair."""
    key: str = Field(..., description="Field label/key")
    value: str = Field(default="", description="Field value")
    confidence: float = Field(default=1.0, ge=0, le=1)


class FormBlock(BaseModel):
    """A form content block with key-value pairs."""
    block_type: BlockType = Field(default=BlockType.FORM)
    fields: list[FormField] = Field(default_factory=list)
    location: BlockLocation = Field(default_factory=BlockLocation)


class ImageBlock(BaseModel):
    """An image content block."""
    block_type: BlockType = Field(default=BlockType.IMAGE)
    image_id: str = Field(..., description="Unique image identifier")
    image_path: str | None = Field(default=None, description="Path to image file")
    image_data: bytes | None = Field(default=None, exclude=True, description="Raw image bytes")
    mime_type: str = Field(default="image/jpeg", description="Image MIME type")
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    location: BlockLocation = Field(default_factory=BlockLocation)
    alt_text: str | None = Field(default=None, description="Alternative text if available")
    caption: str | None = Field(default=None, description="Image caption")
    ocr_text: str | None = Field(default=None, description="OCR extracted text")
    vision_description: str | None = Field(default=None, description="AI vision description")
    image_hash: str | None = Field(default=None, description="Perceptual hash for deduplication")
    
    class Config:
        arbitrary_types_allowed = True


# Union type for all block types
ContentBlock = TextBlock | TableBlock | FormBlock | ImageBlock


class DocumentMetadata(BaseModel):
    """Metadata about the source document."""
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type (pdf, docx, image)")
    mime_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., ge=0)
    page_count: int = Field(default=1, ge=1)
    total_chars: int = Field(default=0, ge=0)
    total_images: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # PDF specific
    pdf_title: str | None = Field(default=None)
    pdf_author: str | None = Field(default=None)
    
    # DOCX specific
    docx_core_properties: dict[str, Any] = Field(default_factory=dict)


class DocumentIR(BaseModel):
    """
    Document Intermediate Representation.
    Unified structure for extracted document content.
    """
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    blocks: list[ContentBlock] = Field(default_factory=list, description="Content blocks")
    
    # Summary fields computed during extraction
    full_text: str = Field(default="", description="Concatenated text content")
    
    @property
    def text_blocks(self) -> list[TextBlock]:
        """Get only text blocks."""
        return [b for b in self.blocks if isinstance(b, TextBlock)]
    
    @property
    def table_blocks(self) -> list[TableBlock]:
        """Get only table blocks."""
        return [b for b in self.blocks if isinstance(b, TableBlock)]
    
    @property
    def image_blocks(self) -> list[ImageBlock]:
        """Get only image blocks."""
        return [b for b in self.blocks if isinstance(b, ImageBlock)]
    
    @property
    def form_blocks(self) -> list[FormBlock]:
        """Get only form blocks."""
        return [b for b in self.blocks if isinstance(b, FormBlock)]
    
    def get_text_for_llm(self, max_chars: int = 100_000) -> str:
        """Get text representation suitable for LLM processing."""
        parts = []
        total_chars = 0
        
        for block in self.blocks:
            if isinstance(block, TextBlock):
                if total_chars + len(block.content) > max_chars:
                    remaining = max_chars - total_chars
                    if remaining > 100:
                        parts.append(block.content[:remaining] + "...")
                    break
                parts.append(block.content)
                total_chars += len(block.content)
            elif isinstance(block, TableBlock):
                table_md = block.to_markdown()
                if total_chars + len(table_md) > max_chars:
                    break
                parts.append(f"\n[TABLE]\n{table_md}\n[/TABLE]\n")
                total_chars += len(table_md)
            elif isinstance(block, FormBlock):
                form_text = "\n".join(f"{f.key}: {f.value}" for f in block.fields)
                if total_chars + len(form_text) > max_chars:
                    break
                parts.append(f"\n[FORM]\n{form_text}\n[/FORM]\n")
                total_chars += len(form_text)
            elif isinstance(block, ImageBlock):
                # Include both OCR text (exact transcription) and vision description
                image_parts = []
                
                if block.ocr_text:
                    # OCR text contains exact text from the image - critical for data extraction
                    image_parts.append(f"Visible Text:\n{block.ocr_text}")
                
                if block.vision_description:
                    image_parts.append(f"Description: {block.vision_description}")
                
                if image_parts:
                    desc = f"\n[IMAGE]\n" + "\n".join(image_parts) + "\n[/IMAGE]\n"
                    if total_chars + len(desc) <= max_chars:
                        parts.append(desc)
                        total_chars += len(desc)
        
        return "\n\n".join(parts)
