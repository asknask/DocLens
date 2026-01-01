"""
Timeout utilities for async operations.
"""
import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any

from app.config import get_settings


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


T = TypeVar('T')


async def with_timeout(
    coro,
    timeout_seconds: int | None = None,
) -> Any:
    """
    Execute a coroutine with a timeout.
    
    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds (uses config default if None)
        
    Returns:
        Result from the coroutine
        
    Raises:
        TimeoutError: If operation times out
    """
    if timeout_seconds is None:
        settings = get_settings()
        timeout_seconds = settings.processing_timeout_seconds
    
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")


def timeout_decorator(timeout_seconds: int | None = None):
    """
    Decorator to add timeout to async functions.
    
    Usage:
        @timeout_decorator(30)
        async def my_function():
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await with_timeout(func(*args, **kwargs), timeout_seconds)
        return wrapper
    return decorator
