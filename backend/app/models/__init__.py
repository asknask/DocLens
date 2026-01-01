# DocLens Models Package
from .api_models import (
    UploadResponse,
    RunRequest,
    RunResponse,
    JobStatusResponse,
    ActionType,
    JobStatus,
    ErrorDetail,
    FileMetadata,
    LimitsInfo,
    ProcessingMetrics,
)
from .ir_models import (
    DocumentIR,
    DocumentMetadata,
    TextBlock,
    TableBlock,
    FormBlock,
    ImageBlock,
    BlockLocation,
)

__all__ = [
    # API Models
    "UploadResponse",
    "RunRequest", 
    "RunResponse",
    "JobStatusResponse",
    "ActionType",
    "JobStatus",
    "ErrorDetail",
    "FileMetadata",
    "LimitsInfo",
    "ProcessingMetrics",
    # IR Models
    "DocumentIR",
    "DocumentMetadata",
    "TextBlock",
    "TableBlock",
    "FormBlock",
    "ImageBlock",
    "BlockLocation",
]
