"""
File security validator.
Prevents path traversal, restricts extensions, enforces size limits.
Used by file-based MCP tools before processing any user-supplied paths.
"""

import os
from pathlib import Path
from typing import List, Optional, Set

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Defaults ─────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS: Set[str] = {
    ".xlsx", ".xls", ".csv", ".json",  # Data files
    ".docx", ".doc",                    # Templates
    ".pdf",                             # Output
    ".txt", ".md",                      # Text
}

MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB


class FileValidationError(Exception):
    """Raised when a file fails security validation."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class FileValidator:
    """
    Validates file paths and operations against security policies.

    Checks:
    1. Path traversal prevention (resolve → check against allowed dirs)
    2. Extension whitelist
    3. File size limits
    4. Symlink detection (reject if target is outside allowed dirs)
    """

    def __init__(
        self,
        allowed_dirs: Optional[List[str]] = None,
        allowed_extensions: Optional[Set[str]] = None,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
    ):
        self.allowed_dirs = [
            Path(d).resolve()
            for d in (allowed_dirs or settings.filesystem_allowed_dirs)
        ]
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.max_file_size = max_file_size

    def validate_path(self, file_path: str) -> Path:
        """
        Validate a file path is safe to access.
        Returns the resolved Path if valid.
        Raises FileValidationError if any check fails.
        """
        path = Path(file_path)

        # 1. Resolve to absolute path (eliminates ../ traversal)
        try:
            resolved = path.resolve(strict=False)
        except (OSError, ValueError) as e:
            raise FileValidationError(
                code="E_FILE_100",
                message=f"Invalid file path: {e}",
            )

        # 2. Check against allowed directories
        if not self._is_within_allowed_dirs(resolved):
            logger.warning(
                "Path traversal blocked",
                requested=str(file_path),
                resolved=str(resolved),
                allowed_dirs=[str(d) for d in self.allowed_dirs],
            )
            raise FileValidationError(
                code="E_FILE_101",
                message="Access denied: path is outside allowed directories.",
            )

        # 3. Check for symlinks pointing outside allowed dirs
        if resolved.exists() and resolved.is_symlink():
            real_target = resolved.resolve()
            if not self._is_within_allowed_dirs(real_target):
                logger.warning(
                    "Symlink escape blocked",
                    symlink=str(resolved),
                    target=str(real_target),
                )
                raise FileValidationError(
                    code="E_FILE_102",
                    message="Access denied: symlink target is outside allowed directories.",
                )

        # 4. Check extension
        ext = resolved.suffix.lower()
        if ext and ext not in self.allowed_extensions:
            raise FileValidationError(
                code="E_FILE_103",
                message=f"File extension '{ext}' is not allowed. "
                f"Allowed: {', '.join(sorted(self.allowed_extensions))}",
            )

        # 5. Check file size (only if file exists)
        if resolved.is_file():
            size = resolved.stat().st_size
            if size > self.max_file_size:
                raise FileValidationError(
                    code="E_FILE_104",
                    message=f"File size ({size:,} bytes) exceeds limit "
                    f"({self.max_file_size:,} bytes).",
                )

        return resolved

    def validate_output_path(self, file_path: str) -> Path:
        """
        Validate that an output path is within allowed dirs.
        Does not check extension or size (output files may vary).
        """
        path = Path(file_path)
        try:
            resolved = path.resolve(strict=False)
        except (OSError, ValueError) as e:
            raise FileValidationError(
                code="E_FILE_100",
                message=f"Invalid output path: {e}",
            )

        if not self._is_within_allowed_dirs(resolved):
            raise FileValidationError(
                code="E_FILE_101",
                message="Access denied: output path is outside allowed directories.",
            )

        return resolved

    def _is_within_allowed_dirs(self, resolved: Path) -> bool:
        """Check if resolved path falls within any allowed directory."""
        for allowed in self.allowed_dirs:
            try:
                resolved.relative_to(allowed)
                return True
            except ValueError:
                continue
        return False


# Singleton instance
file_validator = FileValidator()
