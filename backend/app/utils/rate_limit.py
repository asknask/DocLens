"""
IP-based rate limiting with sliding window.
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from app.config import get_settings


class RateLimiter:
    """IP-based rate limiter with sliding window."""
    
    def __init__(self):
        self.settings = get_settings()
        self._upload_requests: dict[str, list[datetime]] = defaultdict(list)
        self._run_requests: dict[str, list[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_upload_limit(self, ip: str) -> tuple[bool, int]:
        """
        Check if IP can make an upload request.
        
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        return await self._check_limit(
            ip,
            self._upload_requests,
            self.settings.rate_limit_uploads_per_hour,
        )
    
    async def check_run_limit(self, ip: str) -> tuple[bool, int]:
        """
        Check if IP can make a run request.
        
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        return await self._check_limit(
            ip,
            self._run_requests,
            self.settings.rate_limit_runs_per_hour,
        )
    
    async def _check_limit(
        self,
        ip: str,
        request_dict: dict[str, list[datetime]],
        limit: int,
    ) -> tuple[bool, int]:
        """Check rate limit for a specific request type."""
        now = datetime.utcnow()
        window_start = now - timedelta(hours=1)
        
        async with self._lock:
            # Clean up old requests
            request_dict[ip] = [
                dt for dt in request_dict[ip]
                if dt > window_start
            ]
            
            current_count = len(request_dict[ip])
            remaining = limit - current_count
            
            if current_count >= limit:
                return False, 0
            
            # Record this request
            request_dict[ip].append(now)
            return True, remaining - 1
    
    async def get_remaining(self, ip: str) -> dict:
        """Get remaining requests for an IP."""
        now = datetime.utcnow()
        window_start = now - timedelta(hours=1)
        
        async with self._lock:
            # Clean up and count
            self._upload_requests[ip] = [
                dt for dt in self._upload_requests[ip]
                if dt > window_start
            ]
            self._run_requests[ip] = [
                dt for dt in self._run_requests[ip]
                if dt > window_start
            ]
            
            return {
                "uploads_remaining": self.settings.rate_limit_uploads_per_hour - len(self._upload_requests[ip]),
                "runs_remaining": self.settings.rate_limit_runs_per_hour - len(self._run_requests[ip]),
            }
    
    async def cleanup_old_entries(self):
        """Remove entries older than 1 hour."""
        now = datetime.utcnow()
        window_start = now - timedelta(hours=1)
        
        async with self._lock:
            # Clean upload requests
            for ip in list(self._upload_requests.keys()):
                self._upload_requests[ip] = [
                    dt for dt in self._upload_requests[ip]
                    if dt > window_start
                ]
                if not self._upload_requests[ip]:
                    del self._upload_requests[ip]
            
            # Clean run requests
            for ip in list(self._run_requests.keys()):
                self._run_requests[ip] = [
                    dt for dt in self._run_requests[ip]
                    if dt > window_start
                ]
                if not self._run_requests[ip]:
                    del self._run_requests[ip]


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
