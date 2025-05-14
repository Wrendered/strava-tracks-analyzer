"""
Error handling utilities.

This module provides a consistent error handling framework for the application,
including custom exceptions and error logging utilities.
"""

import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast

logger = logging.getLogger(__name__)

# Define type variable for function return type
T = TypeVar('T')


class AppError(Exception):
    """Base class for all application errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the error.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def log(self, level: int = logging.ERROR) -> None:
        """
        Log the error.
        
        Args:
            level: Logging level
        """
        logger.log(level, f"{self.__class__.__name__}: {self.message}")
        if self.details:
            logger.log(level, f"Error details: {self.details}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error to a dictionary.
        
        Returns:
            Dict with error information
        """
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details
        }


class ValidationError(AppError):
    """Error for validation failures."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            details: Additional error details
        """
        details = details or {}
        if field:
            details['field'] = field
        super().__init__(message, details)


class DataError(AppError):
    """Error for data-related issues."""
    
    def __init__(self, message: str, data_source: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the data error.
        
        Args:
            message: Error message
            data_source: Source of the data
            details: Additional error details
        """
        details = details or {}
        if data_source:
            details['data_source'] = data_source
        super().__init__(message, details)


class ConfigurationError(AppError):
    """Error for configuration-related issues."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            details: Additional error details
        """
        details = details or {}
        if config_key:
            details['config_key'] = config_key
        super().__init__(message, details)


class FileError(AppError):
    """Error for file-related issues."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the file error.
        
        Args:
            message: Error message
            file_path: Path to the file
            details: Additional error details
        """
        details = details or {}
        if file_path:
            details['file_path'] = file_path
        super().__init__(message, details)


class AnalysisError(AppError):
    """Error for analysis-related issues."""
    
    def __init__(self, message: str, analysis_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the analysis error.
        
        Args:
            message: Error message
            analysis_type: Type of analysis that failed
            details: Additional error details
        """
        details = details or {}
        if analysis_type:
            details['analysis_type'] = analysis_type
        super().__init__(message, details)


def safe_execute(func: Callable[..., T], *args: Any, **kwargs: Any) -> Optional[T]:
    """
    Execute a function safely, catching and logging exceptions.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or None if an exception occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None


def handle_errors(
    func: Callable[..., T],
    error_map: Dict[Type[Exception], Type[AppError]] = None,
    default_error: Type[AppError] = AppError,
    log_level: int = logging.ERROR
) -> Callable[..., T]:
    """
    Decorator to handle errors in a function.
    
    Args:
        func: Function to decorate
        error_map: Mapping of exception types to AppError types
        default_error: Default AppError type to use
        log_level: Logging level for errors
        
    Returns:
        Decorated function
    """
    error_map = error_map or {}
    
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except tuple(error_map.keys()) as e:
            error_class = error_map[type(e)]
            app_error = error_class(str(e))
            app_error.log(log_level)
            raise app_error
        except Exception as e:
            if isinstance(e, AppError):
                e.log(log_level)
                raise
            
            app_error = default_error(str(e))
            app_error.log(log_level)
            raise app_error from e
    
    return wrapper