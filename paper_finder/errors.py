from __future__ import annotations


class PaperFinderError(Exception):
    """Base exception for all user-visible application errors."""


class ConfigurationError(PaperFinderError):
    """Raised when required configuration is missing or invalid."""


class InputError(PaperFinderError):
    """Raised when user input fails validation."""


class ProviderError(PaperFinderError):
    """Raised when an upstream provider call fails."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ProviderError):
    """Raised when a provider cannot find the requested paper."""
