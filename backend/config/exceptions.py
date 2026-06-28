"""Centralized DRF exception handling for production-friendly API errors."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('hrms.api')


def custom_exception_handler(exc, context):
    """Log server errors and return safe messages when DEBUG is off."""

    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code >= 500:
            logger.exception(
                "API error %s on %s",
                response.status_code,
                context.get('view'),
            )
        return response

    if isinstance(exc, (DatabaseError, IntegrityError)):
        logger.exception("Database error during API request")
        return Response(
            {
                "detail": (
                    "A database error occurred. "
                    "Please try again or contact support."
                )
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
        return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

    logger.exception("Unhandled API exception")
    return Response(
        {"detail": "An unexpected server error occurred."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
