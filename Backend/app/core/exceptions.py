from fastapi import HTTPException

class AppBaseException(Exception):
    """Base exception for domain errors."""
    pass

class TenantNotFoundError(AppBaseException):
    """Raised when tenant context cannot be resolved from the incoming payload."""
    pass

class ProviderNotRegisteredError(AppBaseException):
    """Raised when trying to use an unregistered LLM Provider."""
    pass

class WhatsAppAPIError(AppBaseException):
    """Raised for HTTP API errors when communicating with Meta."""
    pass
