"""
Custom exceptions for the RMIA harvesting module.

Each exception maps to a specific harvest status code.
"""


class HarvestError(Exception):
    """Base class for all harvesting errors."""
    status: str = "FAILED"


class DownloadFailed(HarvestError):
    """HTTP download failed after retries."""
    status = "DOWNLOAD_FAILED"


class InvalidPDF(HarvestError):
    """Downloaded file is not a valid PDF."""
    status = "INVALID_PDF"


class EmptyFile(HarvestError):
    """Downloaded file is empty or below minimum size."""
    status = "EMPTY_FILE"


class AuthRequired(HarvestError):
    """Source requires (re)authentication."""
    status = "AUTH_REQUIRED"


class CaptchaRequired(HarvestError):
    """CAPTCHA or MFA detected — manual intervention required."""
    status = "CAPTCHA_REQUIRED"


class Duplicate(HarvestError):
    """Same PDF (by SHA-256) already exists in storage."""
    status = "DUPLICATE"


class HarvestTimeout(HarvestError):
    """Download or page load timed out."""
    status = "TIMEOUT"


class SourceDisabled(HarvestError):
    """Source is disabled in configuration."""
    status = "DISABLED"


class EditionNotFound(HarvestError):
    """No edition discovered for the requested date."""
    status = "EDITION_NOT_FOUND"
