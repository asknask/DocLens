# DocLens Extract Package
from .pdf_extract import extract_pdf
from .docx_extract import extract_docx
from .image_extract import extract_image
from .text_extract import extract_text

__all__ = [
    "extract_pdf",
    "extract_docx",
    "extract_image",
    "extract_text",
]
