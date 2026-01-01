"""
In-memory job store.
Thread-safe storage for job state with async operations.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from app.models.api_models import ActionType, JobStatus, FileMetadata, ProcessingMetrics


@dataclass
class Job:
    """Represents a document analysis job."""
    job_id: str
    status: JobStatus
    file_metadata: FileMetadata
    created_at: datetime
    expires_at: datetime
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Set after /run
    action: Optional[ActionType] = None
    options: Optional[dict[str, Any]] = None
    refine: Optional[str] = None
    
    # Set after completion
    result: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None
    metrics: Optional[ProcessingMetrics] = None
    
    def to_upload_response(self, limits_info: dict) -> dict:
        """Convert to upload response format."""
        from app.models.api_models import LimitsInfo
        
        return {
            "job_id": self.job_id,
            "status": self.status,
            "file": self.file_metadata.model_dump(),
            "limits": limits_info,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }
    
    def to_status_response(self) -> dict:
        """Convert to job status response format."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "action": self.action,
            "result": self.result,
            "error": self.error,
            "metrics": self.metrics.model_dump() if self.metrics else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobStore:
    """Thread-safe in-memory job storage."""
    
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
    
    async def create_job(
        self,
        job_id: str,
        file_metadata: FileMetadata,
        ttl_minutes: int = 60,
    ) -> Job:
        """Create a new job."""
        now = datetime.utcnow()
        job = Job(
            job_id=job_id,
            status=JobStatus.PENDING,
            file_metadata=file_metadata,
            created_at=now,
            expires_at=now + timedelta(minutes=ttl_minutes),
            updated_at=now,
        )
        
        async with self._lock:
            self._jobs[job_id] = job
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)
    
    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        action: Optional[ActionType] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[dict[str, Any]] = None,
        metrics: Optional[ProcessingMetrics] = None,
    ) -> Optional[Job]:
        """Update job fields."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            
            if status is not None:
                job.status = status
            if action is not None:
                job.action = action
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            if metrics is not None:
                job.metrics = metrics
            
            job.updated_at = datetime.utcnow()
            return job
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        async with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
            return False
    
    async def list_expired_jobs(self) -> list[str]:
        """List job IDs that have expired."""
        now = datetime.utcnow()
        async with self._lock:
            return [
                job_id for job_id, job in self._jobs.items()
                if job.expires_at < now
            ]
    
    async def get_stats(self) -> dict:
        """Get storage statistics."""
        async with self._lock:
            status_counts = {}
            for job in self._jobs.values():
                status_counts[job.status.value] = status_counts.get(job.status.value, 0) + 1
            
            return {
                "total_jobs": len(self._jobs),
                "by_status": status_counts,
            }
    
    async def cleanup_expired(self) -> list[str]:
        """Remove expired jobs and return their IDs."""
        expired = await self.list_expired_jobs()
        for job_id in expired:
            await self.delete_job(job_id)
        return expired


# Global job store instance
_job_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """Get the global job store instance."""
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store
