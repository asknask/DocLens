"""
API Request and Response models using Pydantic v2.
Defines strict enums and nested models for the DocLens API contract.
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Available document analysis actions."""
    SUMMARIZE = "summarize"
    EXTRACT_STRUCTURED = "extract_structured"
    CLASSIFY = "classify"
    QA = "qa"
    TRANSFORM = "transform"


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class ErrorDetail(BaseModel):
    """Error information for failed jobs."""
    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error context")


class FileMetadata(BaseModel):
    """Metadata about the uploaded file."""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    file_type: str = Field(..., description="Detected file category (pdf, docx, image)")
    page_count: int | None = Field(default=None, ge=0, description="Number of pages (PDF only)")
    char_count: int | None = Field(default=None, ge=0, description="Character count (text documents)")
    image_count: int | None = Field(default=None, ge=0, description="Number of embedded images")


class LimitsInfo(BaseModel):
    """Information about configured limits."""
    max_file_size_mb: float = Field(..., description="Maximum file size in MB")
    max_pages: int = Field(..., description="Maximum page count for PDFs")
    max_chars: int = Field(..., description="Maximum character count for DOCX")
    uploads_remaining: int | None = Field(default=None, description="Remaining uploads this hour")
    runs_remaining: int | None = Field(default=None, description="Remaining runs this hour")


class ProcessingMetrics(BaseModel):
    """Metrics about job processing."""
    extraction_time_ms: int | None = Field(default=None, ge=0)
    vision_time_ms: int | None = Field(default=None, ge=0)
    action_time_ms: int | None = Field(default=None, ge=0)
    total_time_ms: int | None = Field(default=None, ge=0)
    pages_processed: int | None = Field(default=None, ge=0)
    vision_pages: int | None = Field(default=None, ge=0)
    tokens_used: int | None = Field(default=None, ge=0)


# ============== API Request Models ==============

class RunRequest(BaseModel):
    """Request body for /api/run endpoint."""
    job_id: str = Field(..., min_length=1, description="Job ID from upload response")
    action: ActionType = Field(..., description="Analysis action to perform")
    options: dict[str, Any] | None = Field(
        default=None,
        description="Action-specific options (e.g., question for QA, schema for extract)"
    )
    refine: str | None = Field(
        default=None, 
        max_length=500,
        description="Free-text instructions to refine output"
    )
    output_format: str | None = Field(
        default="descriptive",
        description="Output format: 'descriptive' for prose or 'json' for structured"
    )


# ============== API Response Models ==============

class UploadResponse(BaseModel):
    """Response from /api/upload endpoint."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    file: FileMetadata = Field(..., description="Uploaded file metadata")
    limits: LimitsInfo = Field(..., description="Configured limits info")
    created_at: datetime = Field(..., description="Job creation timestamp")
    expires_at: datetime = Field(..., description="Job expiration timestamp")


class RunResponse(BaseModel):
    """Response from /api/run endpoint."""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    action: ActionType = Field(..., description="Requested action")
    message: str | None = Field(default=None, description="Status message")


class JobStatusResponse(BaseModel):
    """Response from /api/job/{job_id} endpoint."""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    action: ActionType | None = Field(default=None, description="Requested action if run")
    result: dict[str, Any] | None = Field(default=None, description="Analysis result if completed")
    error: ErrorDetail | None = Field(default=None, description="Error details if failed")
    metrics: ProcessingMetrics | None = Field(default=None, description="Processing metrics")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ============== Action Result Models ==============

class SummarizeResult(BaseModel):
    """Result from summarize action."""
    title: str = Field(..., description="Generated document title")
    summary: str = Field(..., description="Concise summary paragraph")
    bullets: list[str] = Field(default_factory=list, description="Key bullet points")
    key_findings: list[str] = Field(default_factory=list, description="Critical findings")
    risks: list[str] = Field(default_factory=list, description="Identified risks or concerns")


class ExtractedField(BaseModel):
    """A single extracted field with confidence."""
    field: str = Field(..., description="Field name")
    value: Any = Field(..., description="Extracted value")
    confidence: float = Field(..., ge=0, le=1, description="Extraction confidence")


class ExtractStructuredResult(BaseModel):
    """Result from extract_structured action."""
    schema_used: dict[str, str] = Field(..., description="Schema that was applied")
    data: dict[str, Any] = Field(..., description="Extracted data")
    confidence_by_field: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence score for each field"
    )


class ClassifyResult(BaseModel):
    """Result from classify action."""
    label: str = Field(..., description="Classification label")
    confidence: float = Field(..., ge=0, le=1, description="Classification confidence")
    reasons: list[str] = Field(default_factory=list, description="Reasoning for classification")


class Evidence(BaseModel):
    """Evidence supporting an answer."""
    quote: str = Field(..., description="Relevant quote from document")
    location: str | None = Field(default=None, description="Location in document")


class QAResult(BaseModel):
    """Result from qa action."""
    answer: str = Field(..., description="Answer to the question")
    evidence: list[Evidence] = Field(default_factory=list, description="Supporting evidence")
    confidence: float = Field(..., ge=0, le=1, description="Answer confidence")


class TransformResult(BaseModel):
    """Result from transform action."""
    output: str = Field(..., description="Transformed output")
    format_hint: str = Field(default="text", description="Output format hint")
    notes: list[str] = Field(default_factory=list, description="Transformation notes")
