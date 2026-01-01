"""
Background cleanup task for expired jobs.
"""
import asyncio
from typing import Optional

from app.config import get_settings
from app.ingest.storage import get_storage_manager
from .store import get_job_store


_cleanup_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


async def cleanup_expired_jobs():
    """
    Clean up expired jobs and their files.
    
    This performs two-stage cleanup:
    1. Removes expired jobs from the in-memory store
    2. Scans filesystem for orphaned directories older than TTL
    """
    settings = get_settings()
    job_store = get_job_store()
    storage = get_storage_manager()
    
    # Stage 1: Get and delete expired jobs from in-memory store
    expired_job_ids = await job_store.cleanup_expired()
    
    # Delete associated files for expired in-memory jobs
    for job_id in expired_job_ids:
        storage.delete_job_files(job_id)
    
    # Stage 2: Scan filesystem for orphaned directories
    # This catches files left behind after server restart or if job store was cleared
    orphaned_job_ids = await storage.find_expired_job_dirs(settings.storage_ttl_minutes)
    
    orphan_count = 0
    for job_id in orphaned_job_ids:
        # Also try to remove from store in case it exists but wasn't expired
        await job_store.delete_job(job_id)
        # Delete files
        if storage.delete_job_files(job_id):
            orphan_count += 1
    
    return len(expired_job_ids) + orphan_count


async def cleanup_loop():
    """Background loop that runs cleanup periodically."""
    settings = get_settings()
    interval = settings.cleanup_interval_minutes * 60  # Convert to seconds
    
    global _stop_event
    _stop_event = asyncio.Event()
    
    while not _stop_event.is_set():
        try:
            cleaned = await cleanup_expired_jobs()
            if cleaned > 0:
                print(f"[Cleanup] Removed {cleaned} expired jobs")
        except Exception as e:
            print(f"[Cleanup] Error during cleanup: {e}")
        
        # Wait for interval or stop event
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass  # Normal timeout, continue loop


def start_cleanup_task() -> asyncio.Task:
    """Start the background cleanup task."""
    global _cleanup_task
    
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(cleanup_loop())
        print("[Cleanup] Background cleanup task started")
    
    return _cleanup_task


def stop_cleanup_task():
    """Stop the background cleanup task."""
    global _stop_event, _cleanup_task
    
    if _stop_event:
        _stop_event.set()
    
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        print("[Cleanup] Background cleanup task stopped")
