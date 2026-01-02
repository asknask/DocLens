"""
Configuration settings loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""
from pathlib import Path
from typing import Literal
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        # Monorepo structure: look for .env in root first, then local
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # API Configuration
    api_title: str = "DocLens API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"
    
    # AWS Configuration (for Textract fallback)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    textract_enabled: bool = False
    
    # Storage Configuration
    storage_dir: Path = Path("./storage")
    storage_ttl_minutes: int = 60  # Jobs expire after 60 minutes
    cleanup_interval_minutes: int = 5  # Run cleanup every 5 minutes
    
    # File Size Limits (in bytes)
    max_file_size_pdf: int = 20 * 1024 * 1024  # 20MB
    max_file_size_docx: int = 10 * 1024 * 1024  # 10MB
    max_file_size_image: int = 10 * 1024 * 1024  # 10MB
    max_file_size_text: int = 5 * 1024 * 1024  # 5MB
    
    # Document Limits
    max_pdf_pages: int = 50
    max_docx_chars: int = 500_000
    max_docx_images: int = 20
    
    # Vision Limits
    max_vision_pages: int = 10  # Max pages to send to vision
    vision_page_ratio: float = 0.2  # Or 20% of document
    max_vision_images: int = 10  # Max images to process
    
    # Rate Limiting
    rate_limit_uploads_per_hour: int = 5
    rate_limit_runs_per_hour: int = 20
    
    # Processing Limits
    processing_timeout_seconds: int = 60
    
    # CORS Configuration
    cors_origins: list[str] = ["http://localhost:3000"]
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON array or comma-separated string."""
        if isinstance(v, str):
            # Try JSON first
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Fall back to comma-separated
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @property
    def allowed_mime_types(self) -> dict[str, str]:
        """Map of allowed MIME types to file categories."""
        return {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "image/jpeg": "image",
            "image/png": "image", 
            "image/webp": "image",
            "image/gif": "image",
            "text/plain": "text",
        }
    
    def get_max_file_size(self, file_type: Literal["pdf", "docx", "image", "text"]) -> int:
        """Get maximum file size for a given file type."""
        sizes = {
            "pdf": self.max_file_size_pdf,
            "docx": self.max_file_size_docx,
            "image": self.max_file_size_image,
            "text": self.max_file_size_text,
        }
        return sizes.get(file_type, self.max_file_size_image)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
