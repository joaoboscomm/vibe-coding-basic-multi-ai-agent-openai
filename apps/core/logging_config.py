"""
Structured logging configuration with JSON formatting.
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id

        # Add extra fields from the record
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info) if record.exc_info[0] else None,
            }

        return json.dumps(log_data, default=str)


class ContextLogger:
    """
    Logger wrapper that automatically includes context information.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context: dict[str, Any] = {}

    def set_context(self, **kwargs):
        """Set context that will be included in all log messages."""
        self._context.update(kwargs)

    def clear_context(self):
        """Clear all context."""
        self._context.clear()

    def _log(self, level: int, message: str, **kwargs):
        """Log with context."""
        extra = {'extra_data': {**self._context, **kwargs}}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)


def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger instance."""
    return ContextLogger(name)

