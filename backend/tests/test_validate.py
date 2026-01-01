"""
Tests for file validation.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.ingest.validate import validate_file, ValidationError, ValidationResult
from app.ingest.mime import detect_mime_type, get_file_category, is_allowed_mime_type


class TestMimeDetection:
    """Tests for MIME type detection."""
    
    def test_detect_pdf(self):
        """Test PDF detection."""
        pdf_bytes = b"%PDF-1.4 some content"
        assert detect_mime_type(pdf_bytes) == "application/pdf"
    
    def test_detect_jpeg(self):
        """Test JPEG detection."""
        jpeg_bytes = b"\xff\xd8\xff\xe0 some content"
        assert detect_mime_type(jpeg_bytes) == "image/jpeg"
    
    def test_detect_png(self):
        """Test PNG detection."""
        png_bytes = b"\x89PNG\r\n\x1a\n some content"
        assert detect_mime_type(png_bytes) == "image/png"
    
    def test_detect_gif(self):
        """Test GIF detection."""
        gif_bytes = b"GIF89a some content"
        assert detect_mime_type(gif_bytes) == "image/gif"
    
    def test_detect_webp(self):
        """Test WebP detection."""
        webp_bytes = b"RIFF\x00\x00\x00\x00WEBP some content"
        assert detect_mime_type(webp_bytes) == "image/webp"
    
    def test_detect_docx(self):
        """Test DOCX (ZIP) detection."""
        docx_bytes = b"PK\x03\x04 some content"
        mime = detect_mime_type(docx_bytes)
        assert mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    def test_detect_unknown(self):
        """Test unknown file type."""
        unknown_bytes = b"random bytes here"
        assert detect_mime_type(unknown_bytes) is None
    
    def test_detect_too_short(self):
        """Test handling of too-short data."""
        short_bytes = b"abc"
        assert detect_mime_type(short_bytes) is None


class TestFileCategory:
    """Tests for file category mapping."""
    
    def test_pdf_category(self):
        """Test PDF category."""
        assert get_file_category("application/pdf") == "pdf"
    
    def test_docx_category(self):
        """Test DOCX category."""
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert get_file_category(mime) == "docx"
    
    def test_image_categories(self):
        """Test image categories."""
        assert get_file_category("image/jpeg") == "image"
        assert get_file_category("image/png") == "image"
        assert get_file_category("image/gif") == "image"
        assert get_file_category("image/webp") == "image"
    
    def test_unknown_category(self):
        """Test unknown MIME type."""
        assert get_file_category("application/octet-stream") is None


class TestAllowedMimeTypes:
    """Tests for allowed MIME type checking."""
    
    def test_allowed_types(self):
        """Test that expected types are allowed."""
        assert is_allowed_mime_type("application/pdf") == True
        assert is_allowed_mime_type("image/jpeg") == True
        assert is_allowed_mime_type("image/png") == True
    
    def test_disallowed_types(self):
        """Test that unexpected types are not allowed."""
        assert is_allowed_mime_type("application/javascript") == False
        assert is_allowed_mime_type("text/html") == False
        assert is_allowed_mime_type(None) == False


class TestValidateFile:
    """Tests for file validation."""
    
    def test_unsupported_file_type(self):
        """Test rejection of unsupported file types."""
        with pytest.raises(ValidationError) as exc_info:
            validate_file(b"random bytes", "test.txt")
        
        assert exc_info.value.code == "unsupported_file_type"
    
    def test_file_too_large(self):
        """Test rejection of oversized files."""
        # Create a "PDF" that's too large
        with patch("app.ingest.validate.get_settings") as mock_settings:
            settings = MagicMock()
            settings.get_max_file_size.return_value = 100  # 100 bytes max
            settings.max_pdf_pages = 50
            mock_settings.return_value = settings
            
            large_pdf = b"%PDF-1.4" + b"x" * 200
            
            with pytest.raises(ValidationError) as exc_info:
                validate_file(large_pdf, "large.pdf")
            
            assert exc_info.value.code == "file_too_large"
    
    def test_valid_image(self):
        """Test validation of a valid image."""
        # Create minimal valid JPEG
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 100
        
        with patch("app.ingest.validate.get_settings") as mock_settings:
            settings = MagicMock()
            settings.get_max_file_size.return_value = 10 * 1024 * 1024  # 10MB
            settings.max_file_size_image = 10 * 1024 * 1024
            mock_settings.return_value = settings
            
            result = validate_file(jpeg_bytes, "test.jpg")
            
            assert result.valid == True
            assert result.file_type == "image"
            assert result.mime_type == "image/jpeg"
