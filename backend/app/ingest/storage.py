"""
Temporary file storage for uploaded documents.
Manages job directories with TTL-based cleanup.
"""
import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import uuid

import aiofiles

from app.config import get_settings


class StorageManager:
    """Manages temporary file storage for jobs."""
    
    def __init__(self):
        self.settings = get_settings()
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.settings.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_job_id(self) -> str:
        """Generate a unique job ID."""
        return str(uuid.uuid4())
    
    def get_job_dir(self, job_id: str) -> Path:
        """Get the directory path for a job."""
        return self.settings.storage_dir / job_id
    
    def get_file_path(self, job_id: str, filename: str) -> Path:
        """Get the full path for a file within a job directory."""
        return self.get_job_dir(job_id) / filename
    
    async def save_uploaded_file(
        self,
        job_id: str,
        filename: str,
        file_bytes: bytes,
    ) -> Path:
        """
        Save an uploaded file to the job directory.
        
        Args:
            job_id: Job identifier
            filename: Original filename (sanitized)
            file_bytes: File content
            
        Returns:
            Path to the saved file
        """
        job_dir = self.get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        file_path = job_dir / safe_filename
        
        # Write file asynchronously
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)
        
        # Write metadata
        meta_path = job_dir / "_metadata.txt"
        async with aiofiles.open(meta_path, "w") as f:
            await f.write(f"created_at={datetime.utcnow().isoformat()}\n")
            await f.write(f"filename={filename}\n")
        
        return file_path
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        # Get just the base name, no path components
        safe = Path(filename).name
        # Replace potentially problematic characters
        for char in ['..', '/', '\\', '\x00']:
            safe = safe.replace(char, '_')
        # Limit length
        if len(safe) > 200:
            name_part = safe[:190]
            ext = Path(safe).suffix[:10]
            safe = f"{name_part}{ext}"
        return safe or "uploaded_file"
    
    async def read_file(self, job_id: str, filename: str) -> Optional[bytes]:
        """Read a file from job storage."""
        file_path = self.get_file_path(job_id, filename)
        if not file_path.exists():
            return None
        
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()
    
    def delete_job_files(self, job_id: str) -> bool:
        """
        Delete all files for a job.
        
        Returns:
            True if deleted, False if job directory didn't exist
        """
        job_dir = self.get_job_dir(job_id)
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
            return True
        return False
    
    def list_job_ids(self) -> list[str]:
        """List all job IDs in storage."""
        if not self.settings.storage_dir.exists():
            return []
        return [
            d.name for d in self.settings.storage_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
    
    async def get_job_created_at(self, job_id: str) -> Optional[datetime]:
        """Get the creation time of a job from metadata."""
        meta_path = self.get_job_dir(job_id) / "_metadata.txt"
        if not meta_path.exists():
            return None
        
        try:
            async with aiofiles.open(meta_path, "r") as f:
                content = await f.read()
            
            for line in content.split("\n"):
                if line.startswith("created_at="):
                    iso_str = line.split("=", 1)[1].strip()
                    return datetime.fromisoformat(iso_str)
        except Exception:
            pass
        
        return None
    
    def get_storage_stats(self) -> dict:
        """Get storage statistics."""
        if not self.settings.storage_dir.exists():
            return {"total_jobs": 0, "total_size_bytes": 0}
        
        total_size = 0
        job_count = 0
        
        for job_dir in self.settings.storage_dir.iterdir():
            if job_dir.is_dir() and not job_dir.name.startswith("_"):
                job_count += 1
                for file_path in job_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
        
        return {
            "total_jobs": job_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    async def find_expired_job_dirs(self, ttl_minutes: int) -> list[str]:
        """
        Find job directories that have expired based on filesystem metadata.
        
        This scans the storage folder directly, catching orphaned directories
        that may not exist in the in-memory job store (e.g., after server restart).
        
        Args:
            ttl_minutes: Maximum age in minutes before a job is considered expired
            
        Returns:
            List of expired job IDs
        """
        if not self.settings.storage_dir.exists():
            return []
        
        expired_job_ids = []
        now = datetime.utcnow()
        ttl_delta = timedelta(minutes=ttl_minutes)
        
        for job_dir in self.settings.storage_dir.iterdir():
            if not job_dir.is_dir() or job_dir.name.startswith("_"):
                continue
            
            job_id = job_dir.name
            created_at = await self.get_job_created_at(job_id)
            
            if created_at is None:
                # No metadata file - use directory modification time as fallback
                try:
                    dir_mtime = datetime.utcfromtimestamp(job_dir.stat().st_mtime)
                    if now - dir_mtime > ttl_delta:
                        expired_job_ids.append(job_id)
                except OSError:
                    # Directory may have been deleted, skip
                    continue
            else:
                # Use metadata timestamp
                if now - created_at > ttl_delta:
                    expired_job_ids.append(job_id)
        
        return expired_job_ids


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


# Convenience functions
async def save_uploaded_file(job_id: str, filename: str, file_bytes: bytes) -> Path:
    """Save an uploaded file to storage."""
    return await get_storage_manager().save_uploaded_file(job_id, filename, file_bytes)


def get_file_path(job_id: str, filename: str) -> Path:
    """Get the path for a file in job storage."""
    return get_storage_manager().get_file_path(job_id, filename)


def delete_job_files(job_id: str) -> bool:
    """Delete all files for a job."""
    return get_storage_manager().delete_job_files(job_id)
