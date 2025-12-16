"""
Custom exception handling for the API.
"""
import logging
import traceback

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats errors consistently
    and logs them with correlation IDs.
    """
    # Get the standard response
    response = exception_handler(exc, context)

    # Get correlation ID from request if available
    request = context.get('request')
    correlation_id = getattr(request, 'correlation_id', None) if request else None

    if response is not None:
        # Format the response
        error_response = {
            'error': True,
            'message': str(exc),
            'status_code': response.status_code,
        }

        if correlation_id:
            error_response['correlation_id'] = correlation_id

        # Add detail if available
        if hasattr(exc, 'detail'):
            error_response['detail'] = exc.detail

        response.data = error_response

    else:
        # Handle unexpected exceptions
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                'correlation_id': correlation_id,
                'traceback': traceback.format_exc(),
            }
        )

        response = Response(
            {
                'error': True,
                'message': 'An unexpected error occurred',
                'status_code': 500,
                'correlation_id': correlation_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response


class AgentExecutionError(Exception):
    """Exception raised when an agent fails to execute."""
    pass


class ToolExecutionError(Exception):
    """Exception raised when a tool fails to execute."""
    pass


class RAGSearchError(Exception):
    """Exception raised when RAG search fails."""
    pass

