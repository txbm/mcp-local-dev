"""Logging utilities."""
from functools import wraps
import structlog
from typing import Any, Callable, TypeVar

# Type variables for generic function decorators
F = TypeVar('F', bound=Callable[..., Any])

# Configure structured logging
logger = structlog.get_logger()

def with_logging(*, context: str) -> Callable[[F], F]:
    """Decorator to add structured logging to functions.
    
    Args:
        context: Context name for log entries
        
    Returns:
        Decorated function with logging
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            bound_logger = logger.bind(
                context=context,
                function=func.__name__
            )
            
            # Log function call
            bound_logger.info(
                "function_called",
                args=args,
                kwargs={k: v for k, v in kwargs.items() if k != "env"}  # Don't log env vars
            )
            
            try:
                result = await func(*args, **kwargs)
                
                # Log success
                bound_logger.info(
                    "function_succeeded",
                    result_type=type(result).__name__
                )
                
                return result
                
            except Exception as e:
                # Log error with details
                bound_logger.error(
                    "function_failed",
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise
                
        return wrapper  # type: ignore
    return decorator


def log_runtime_error(error: Exception, context: Dict[str, Any]) -> None:
    """Log runtime errors with additional context.
    
    Args:
        error: Exception that occurred
        context: Additional context information
    """
    logger.error(
        "runtime_error",
        error_type=type(error).__name__,
        error_message=str(error),
        **context
    )


def format_process_error(error: Exception, command: str) -> str:
    """Format process execution error message.
    
    Args:
        error: Process execution error
        command: Command that was attempted
        
    Returns:
        Formatted error message
    """
    return (
        f"Failed to execute command: {command}\n"
        f"Error: {type(error).__name__}: {str(error)}"
    )