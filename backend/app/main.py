"""
DocLens FastAPI Application.
Main entry point with API endpoints and lifespan management.
"""
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, Settings
from app.models.api_models import (
    ActionType,
    JobStatus,
    RunRequest,
    RunResponse,
    UploadResponse,
    JobStatusResponse,
    FileMetadata,
    LimitsInfo,
    ErrorDetail,
    ProcessingMetrics,
)
from app.ingest.validate import validate_file, ValidationError
from app.ingest.storage import get_storage_manager
from app.extract import extract_pdf, extract_docx, extract_image, extract_text
from app.vision import select_pages_for_vision, select_images_for_vision, describe_images_batch
from app.vision.langchain_vision import update_image_blocks_with_descriptions
from app.extract.pdf_extract import get_page_char_counts, render_specific_pages
from app.models.ir_models import ImageBlock
from app.actions import execute_action
from app.jobs import get_job_store, start_cleanup_task, stop_cleanup_task
from app.utils.rate_limit import get_rate_limiter
from app.utils.timeouts import with_timeout, TimeoutError


# Dependency for settings
def get_settings_dep() -> Settings:
    return get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global _startup_time
    
    # Startup
    print("🚀 DocLens API starting up...")
    _startup_time = datetime.utcnow()
    settings = get_settings()
    
    # Ensure storage directory exists
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Start cleanup task
    start_cleanup_task()
    
    yield
    
    # Shutdown
    print("👋 DocLens API shutting down...")
    stop_cleanup_task()


# Track startup time for uptime calculation
_startup_time: datetime | None = None

# Create FastAPI app
app = FastAPI(
    title="DocLens API",
    description="Document Analyzer API - Upload documents and analyze with AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_limits_info(settings: Settings, remaining: dict | None = None) -> dict:
    """Build limits info response."""
    file_type_sizes = {
        "pdf": settings.max_file_size_pdf,
        "docx": settings.max_file_size_docx,
        "image": settings.max_file_size_image,
    }
    max_size = max(file_type_sizes.values())
    
    info = {
        "max_file_size_mb": round(max_size / (1024 * 1024), 1),
        "max_pages": settings.max_pdf_pages,
        "max_chars": settings.max_docx_chars,
    }
    
    if remaining:
        info["uploads_remaining"] = remaining.get("uploads_remaining")
        info["runs_remaining"] = remaining.get("runs_remaining")
    
    return info


# ============== Health Check ==============

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Coolify and other monitoring services.
    
    Returns:
        - status: "healthy" if the service is running
        - service: Name of the service
        - version: API version
        - timestamp: Current UTC timestamp
        - uptime_seconds: Time since service started (if available)
    """
    response = {
        "status": "healthy",
        "service": "doclens-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if _startup_time:
        uptime = (datetime.utcnow() - _startup_time).total_seconds()
        response["uptime_seconds"] = int(uptime)
    
    return response


# ============== Upload Endpoint ==============

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: Annotated[UploadFile, File(description="Document file to upload")],
    settings: Settings = Depends(get_settings_dep),
):
    """
    Upload a document for analysis.
    
    Supports PDF, DOCX, and image files (JPEG, PNG, WebP, GIF).
    Returns a job_id to use for subsequent operations.
    """
    client_ip = get_client_ip(request)
    rate_limiter = get_rate_limiter()
    
    # Check rate limit
    allowed, remaining = await rate_limiter.check_upload_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Upload rate limit exceeded. Try again later.",
            }
        )
    
    # Read file content
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")
    
    # Validate file
    try:
        validation = validate_file(file_bytes, file.filename or "uploaded_file")
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": e.code,
                "message": e.message,
                "details": e.details,
            }
        )
    
    # Create job
    storage = get_storage_manager()
    job_store = get_job_store()
    
    job_id = storage.generate_job_id()
    
    # Save file
    await storage.save_uploaded_file(job_id, file.filename or "uploaded_file", file_bytes)
    
    # Create file metadata
    file_metadata = FileMetadata(
        filename=file.filename or "uploaded_file",
        content_type=validation.mime_type,
        size_bytes=validation.size_bytes,
        file_type=validation.file_type,
        page_count=validation.page_count,
        char_count=validation.char_count,
        image_count=validation.image_count,
    )
    
    # Create job record
    job = await job_store.create_job(
        job_id=job_id,
        file_metadata=file_metadata,
        ttl_minutes=settings.storage_ttl_minutes,
    )
    
    # Get remaining requests for limits info
    remaining_info = await rate_limiter.get_remaining(client_ip)
    
    return UploadResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        file=file_metadata,
        limits=LimitsInfo(**get_limits_info(settings, remaining_info)),
        created_at=job.created_at,
        expires_at=job.expires_at,
    )


# ============== Run Endpoint ==============

@app.post("/api/run", response_model=RunResponse)
async def run_action(
    request: Request,
    run_request: RunRequest,
    settings: Settings = Depends(get_settings_dep),
):
    """
    Run an analysis action on an uploaded document.
    
    Actions:
    - summarize: Generate document summary
    - extract_structured: Extract entities and structured data
    - classify: Classify document type
    - qa: Answer questions about the document (requires 'question' in options)
    - transform: Transform document to different format
    """
    client_ip = get_client_ip(request)
    rate_limiter = get_rate_limiter()
    
    # Check rate limit
    allowed, _ = await rate_limiter.check_run_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "Run rate limit exceeded. Try again later.",
            }
        )
    
    # Get job
    job_store = get_job_store()
    job = await job_store.get_job(run_request.job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Job is already processing")
    
    if job.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Job has expired")
    
    # Update job status
    await job_store.update_job(
        job.job_id,
        status=JobStatus.PROCESSING,
        action=run_request.action,
    )
    
    # Process in background (for PoC, we do it synchronously but with timeout)
    try:
        result, metrics = await process_job(
            job_id=job.job_id,
            action=run_request.action,
            file_metadata=job.file_metadata,
            options=run_request.options,
            refine=run_request.refine,
            output_format=run_request.output_format,
            settings=settings,
        )
        
        # Update job with result
        await job_store.update_job(
            job.job_id,
            status=JobStatus.COMPLETED,
            result=result,
            metrics=metrics,
        )
        
        return RunResponse(
            job_id=job.job_id,
            status=JobStatus.COMPLETED,
            action=run_request.action,
            message="Analysis completed successfully",
        )
        
    except TimeoutError:
        await job_store.update_job(
            job.job_id,
            status=JobStatus.FAILED,
            error={"code": "timeout", "message": "Processing timed out"},
        )
        raise HTTPException(status_code=504, detail="Processing timed out")
    
    except Exception as e:
        await job_store.update_job(
            job.job_id,
            status=JobStatus.FAILED,
            error={"code": "processing_error", "message": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")


async def process_job(
    job_id: str,
    action: ActionType,
    file_metadata: FileMetadata,
    options: dict | None,
    refine: str | None,
    output_format: str | None,
    settings: Settings,
) -> tuple[dict, ProcessingMetrics]:
    """Process a job with extraction, vision, and action execution."""
    start_time = time.time()
    metrics = {
        "extraction_time_ms": 0,
        "vision_time_ms": 0,
        "action_time_ms": 0,
        "pages_processed": 0,
        "vision_pages": 0,
    }
    
    storage = get_storage_manager()
    job_dir = storage.get_job_dir(job_id)
    
    # Read file
    files = list(job_dir.glob("*"))
    file_path = next(
        (f for f in files if not f.name.startswith("_")),
        None
    )
    if not file_path:
        raise ValueError("File not found in job directory")
    
    file_bytes = file_path.read_bytes()
    
    # Extract document content
    extraction_start = time.time()
    
    if file_metadata.file_type == "pdf":
        document_ir = extract_pdf(file_bytes, file_metadata.filename, job_dir)
        metrics["pages_processed"] = document_ir.metadata.page_count
    elif file_metadata.file_type == "docx":
        document_ir = extract_docx(file_bytes, file_metadata.filename, job_dir)
    elif file_metadata.file_type == "text":
        document_ir = extract_text(file_bytes, file_metadata.filename, job_dir)
    else:  # image
        document_ir = extract_image(
            file_bytes,
            file_metadata.filename,
            file_metadata.content_type,
            job_dir,
        )
    
    metrics["extraction_time_ms"] = int((time.time() - extraction_start) * 1000)
    
    # Vision processing for images or low-text pages
    vision_start = time.time()
    
    if file_metadata.file_type == "pdf":
        # Check if any pages need vision (low-text pages)
        page_char_counts = get_page_char_counts(file_bytes)
        vision_pages = select_pages_for_vision(page_char_counts)
        
        if vision_pages:
            # Render and process pages
            image_blocks = render_specific_pages(file_bytes, vision_pages, job_dir)
            if image_blocks:
                descriptions = await describe_images_batch(image_blocks)
                update_image_blocks_with_descriptions(image_blocks, descriptions)
                document_ir.blocks.extend(image_blocks)
                metrics["vision_pages"] = len(vision_pages)
        
        # Also process embedded images extracted from the PDF
        embedded_images = [b for b in document_ir.blocks if isinstance(b, ImageBlock) and not b.vision_description]
        if embedded_images:
            descriptions = await describe_images_batch(embedded_images)
            update_image_blocks_with_descriptions(embedded_images, descriptions)
            metrics["vision_pages"] = metrics.get("vision_pages", 0) + len(embedded_images)
    
    elif file_metadata.file_type == "image":
        # Always process standalone images with vision
        images_to_process = select_images_for_vision(document_ir)
        if images_to_process:
            descriptions = await describe_images_batch(images_to_process)
            update_image_blocks_with_descriptions(images_to_process, descriptions)
            metrics["vision_pages"] = len(images_to_process)
    
    elif file_metadata.file_type == "docx":
        # Process embedded images
        images_to_process = select_images_for_vision(document_ir)
        if images_to_process:
            descriptions = await describe_images_batch(images_to_process)
            update_image_blocks_with_descriptions(images_to_process, descriptions)
            metrics["vision_pages"] = len(images_to_process)
    
    metrics["vision_time_ms"] = int((time.time() - vision_start) * 1000)
    
    # Execute action with timeout
    action_start = time.time()
    
    result = await with_timeout(
        execute_action(
            action=action,
            document_ir=document_ir,
            options=options,
            refine=refine,
            output_format=output_format,
        ),
        timeout_seconds=settings.processing_timeout_seconds,
    )
    
    metrics["action_time_ms"] = int((time.time() - action_start) * 1000)
    metrics["total_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result, ProcessingMetrics(**metrics)


# ============== Job Status Endpoint ==============

@app.get("/api/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status and result of a job.
    
    Poll this endpoint to check if processing is complete.
    """
    job_store = get_job_store()
    job = await job_store.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        action=job.action,
        result=job.result,
        error=ErrorDetail(**job.error) if job.error else None,
        metrics=job.metrics,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ============== Stats Endpoint (Debug) ==============

@app.get("/api/stats")
async def get_stats(settings: Settings = Depends(get_settings_dep)):
    """Get API statistics (debug endpoint)."""
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    
    job_store = get_job_store()
    storage = get_storage_manager()
    
    job_stats = await job_store.get_stats()
    storage_stats = storage.get_storage_stats()
    
    return {
        "jobs": job_stats,
        "storage": storage_stats,
    }


# Error handlers
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        }
    )
