"""Input validation and security checks.

Features:
- Path traversal prevention
- Command injection prevention
- File type validation
- Input sanitization
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

# from src.exceptions import SecurityError  # Future use

logger = structlog.get_logger()


class SecurityValidator:
    """Security validation for user inputs."""

    # Dangerous patterns for path traversal and injection
    # Note: Split into different categories for different validation contexts
    DANGEROUS_PATH_PATTERNS = [
        r"\.\.",  # Parent directory
        r"~",  # Home directory expansion
        r"\x00",  # Null byte
    ]
    
    DANGEROUS_COMMAND_PATTERNS = [
        r"\$\{",  # Variable expansion ${...}
        r"\$\(",  # Command substitution $(...)
        r"\$[A-Za-z_]",  # Environment variable expansion $VAR
        r"`",  # Command substitution with backticks
        r";\s*(?:rm|del|format|sudo|curl|wget)",  # Command chaining with dangerous commands
        r"&&\s*(?:rm|del|format|sudo|curl|wget)",  # AND chaining with dangerous commands
        r"\|\|",  # OR chaining
        r">\s*/dev/",  # Dangerous output redirection
        r"<\s*/dev/",  # Dangerous input redirection
        r"\|\s*(?:sh|bash|cmd|powershell)",  # Piping to shells
        r"#.*(?:rm|del|format|sudo)",  # Comments with dangerous commands
    ]
    
    # Keep original for backward compatibility - now combines both
    DANGEROUS_PATTERNS = DANGEROUS_PATH_PATTERNS + DANGEROUS_COMMAND_PATTERNS

    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".md",
        ".txt",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
        ".r",
        ".scala",
        ".clj",
        ".hs",
        ".elm",
        ".vue",
        ".svelte",
        ".lock",
        # Image formats for image processing
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".tiff",
        ".tif",
    }

    # Forbidden filenames and patterns
    FORBIDDEN_FILENAMES = {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        ".ssh",
        ".aws",
        ".docker",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "shadow",
        "passwd",
        "hosts",
        "sudoers",
        ".bash_history",
        ".zsh_history",
        ".mysql_history",
        ".psql_history",
    }

    # Dangerous file patterns
    DANGEROUS_FILE_PATTERNS = [
        r".*\.key$",  # Key files
        r".*\.pem$",  # Certificate files
        r".*\.p12$",  # Certificate files
        r".*\.pfx$",  # Certificate files
        r".*\.crt$",  # Certificate files
        r".*\.cer$",  # Certificate files
        r".*_rsa$",  # SSH keys
        r".*_dsa$",  # SSH keys
        r".*_ecdsa$",  # SSH keys
        r".*\.exe$",  # Executables
        r".*\.dll$",  # Windows libraries
        r".*\.so$",  # Shared objects
        r".*\.dylib$",  # macOS libraries
        r".*\.bat$",  # Batch files
        r".*\.cmd$",  # Command files
        r".*\.msi$",  # Installers
        r".*\.rar$",  # Archives (potentially dangerous)
    ]

    def __init__(self, approved_directory: Path, flexible_mode: bool = False):
        """Initialize validator with approved directory.
        
        Args:
            approved_directory: Base directory for file operations
            flexible_mode: If True, allows operations in subdirectories of approved_directory
                          If False, strict mode - only exact approved_directory
        """
        self.approved_directory = approved_directory.resolve()
        self.flexible_mode = flexible_mode
        logger.info(
            "Security validator initialized",
            approved_directory=str(self.approved_directory),
            flexible_mode=flexible_mode,
        )

    def validate_path(
        self, user_path: str, current_dir: Optional[Path] = None
    ) -> Tuple[bool, Optional[Path], Optional[str]]:
        """Validate and resolve user-provided path.

        Returns:
            Tuple of (is_valid, resolved_path, error_message)
        """
        try:
            # Basic input validation
            if not user_path or not user_path.strip():
                return False, None, "Empty path not allowed"

            user_path = user_path.strip()

            # Check for dangerous path patterns (more restrictive for paths)
            for pattern in self.DANGEROUS_PATH_PATTERNS:
                if re.search(pattern, user_path, re.IGNORECASE):
                    logger.warning(
                        "Dangerous pattern detected in path",
                        path=user_path,
                        pattern=pattern,
                    )
                    return (
                        False,
                        None,
                        f"Invalid path: contains forbidden pattern '{pattern}'",
                    )

            # Handle path resolution
            current_dir = current_dir or self.approved_directory

            if user_path.startswith("/"):
                # Absolute path - use as-is
                target = Path(user_path)
            else:
                # Relative path
                target = current_dir / user_path

            # Resolve path and check boundaries
            target = target.resolve()

            # Ensure target is within approved directory
            if not self._is_within_directory(target, self.approved_directory):
                if self.flexible_mode:
                    # In flexible mode, check if we're still within a reasonable subdirectory
                    try:
                        # Allow current working directory if it's a subdirectory of approved_directory
                        if current_dir and self._is_within_directory(current_dir, self.approved_directory):
                            # If target is in current_dir and current_dir is safe, allow it
                            if self._is_within_directory(target, current_dir):
                                logger.debug(
                                    "Path allowed in flexible mode",
                                    requested_path=user_path,
                                    resolved_path=str(target),
                                    current_dir=str(current_dir),
                                )
                                return True, target, None
                    except Exception:
                        pass
                
                logger.warning(
                    "Path traversal attempt detected",
                    requested_path=user_path,
                    resolved_path=str(target),
                    approved_directory=str(self.approved_directory),
                    flexible_mode=self.flexible_mode,
                )
                return False, None, "Access denied: path outside approved directory"

            logger.debug(
                "Path validation successful",
                original_path=user_path,
                resolved_path=str(target),
            )
            return True, target, None

        except Exception as e:
            logger.error("Path validation error", path=user_path, error=str(e))
            return False, None, f"Invalid path: {str(e)}"

    def _is_within_directory(self, path: Path, directory: Path) -> bool:
        """Check if path is within directory."""
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            return False

    def validate_filename(self, filename: str) -> Tuple[bool, Optional[str]]:
        """Validate uploaded filename.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic checks
        if not filename or not filename.strip():
            return False, "Empty filename not allowed"

        filename = filename.strip()

        # Check for path separators in filename
        if "/" in filename or "\\" in filename:
            logger.warning("Path separator in filename", filename=filename)
            return False, "Invalid filename: contains path separators"

        # Check for forbidden patterns in filenames (use path patterns, not command patterns)
        for pattern in self.DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                logger.warning(
                    "Dangerous pattern in filename", filename=filename, pattern=pattern
                )
                return False, "Invalid filename: contains forbidden pattern"

        # Check for forbidden filenames
        if filename.lower() in {name.lower() for name in self.FORBIDDEN_FILENAMES}:
            logger.warning("Forbidden filename", filename=filename)
            return False, f"Forbidden filename: {filename}"

        # Check for dangerous file patterns
        for pattern in self.DANGEROUS_FILE_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE):
                logger.warning(
                    "Dangerous file pattern", filename=filename, pattern=pattern
                )
                return False, f"File type not allowed: {filename}"

        # Check extension
        path_obj = Path(filename)
        ext = path_obj.suffix.lower()

        if ext and ext not in self.ALLOWED_EXTENSIONS:
            logger.warning(
                "File extension not allowed", filename=filename, extension=ext
            )
            return False, f"File type not allowed: {ext}"

        # Check for hidden files (starting with .)
        if filename.startswith(".") and filename not in {".gitignore", ".gitkeep"}:
            logger.warning("Hidden file upload attempt", filename=filename)
            return False, "Hidden files not allowed"

        # Check filename length
        if len(filename) > 255:
            return False, "Filename too long (max 255 characters)"

        logger.debug("Filename validation successful", filename=filename)
        return True, None

    def sanitize_command_input(self, text: str) -> str:
        """Sanitize text input for commands.

        This removes potentially dangerous characters but preserves
        the structure needed for legitimate commands.
        """
        if not text:
            return ""

        # Remove dangerous characters but preserve basic ones
        # Note: This is very restrictive - adjust based on actual needs
        sanitized = re.sub(r"[`$;|&<>#\x00-\x1f\x7f]", "", text)

        # Limit length to prevent buffer overflow attacks
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(
                "Command input truncated",
                original_length=len(text),
                truncated_length=len(sanitized),
            )

        # Remove excessive whitespace
        sanitized = " ".join(sanitized.split())

        if sanitized != text:
            logger.debug(
                "Command input sanitized",
                original=text[:100],  # Log first 100 chars
                sanitized=sanitized[:100],
            )

        return sanitized

    def sanitize_command_input_lenient(self, text: str) -> str:
        """Sanitize text input for commands with lenient rules for image processing context.

        This allows Markdown characters like # while still blocking dangerous patterns.
        """
        if not text:
            return ""

        # Remove dangerous characters but allow Markdown formatting
        # Allow # for headers, * for emphasis, etc.
        sanitized = re.sub(r"[`$;|&<>\x00-\x1f\x7f]", "", text)

        # Limit length to prevent buffer overflow attacks
        max_length = 5000  # Higher limit for image context with detailed prompts
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            logger.warning(
                "Command input truncated (lenient)",
                original_length=len(text),
                truncated_length=len(sanitized),
            )

        # Keep original whitespace structure for formatted text
        # Only collapse excessive runs of whitespace
        sanitized = re.sub(r'\s{3,}', '  ', sanitized)

        if sanitized != text:
            logger.debug(
                "Command input sanitized (lenient)",
                original=text[:100],  # Log first 100 chars
                sanitized=sanitized[:100],
            )

        return sanitized

    def validate_command_args(
        self, args: List[str]
    ) -> Tuple[bool, List[str], Optional[str]]:
        """Validate and sanitize command arguments.

        Returns:
            Tuple of (is_valid, sanitized_args, error_message)
        """
        if not args:
            return True, [], None

        sanitized_args = []

        for arg in args:
            # Check for dangerous command patterns in arguments
            for pattern in self.DANGEROUS_COMMAND_PATTERNS:
                if re.search(pattern, arg, re.IGNORECASE):
                    logger.warning(
                        "Dangerous pattern in command arg", arg=arg, pattern=pattern
                    )
                    return False, [], "Invalid argument: contains forbidden pattern"

            # Sanitize argument
            sanitized = self.sanitize_command_input(arg)
            if not sanitized and arg:  # If original had content but sanitized is empty
                logger.warning("Command argument completely sanitized", original=arg)
                return (
                    False,
                    [],
                    f"Invalid argument: '{arg}' contains only forbidden characters",
                )

            sanitized_args.append(sanitized)

        return True, sanitized_args, None

    def is_safe_directory_name(self, dirname: str) -> bool:
        """Check if directory name is safe for creation."""
        if not dirname or not dirname.strip():
            return False

        dirname = dirname.strip()

        # Check for dangerous patterns in directory names (use path patterns)
        for pattern in self.DANGEROUS_PATH_PATTERNS:
            if re.search(pattern, dirname, re.IGNORECASE):
                return False

        # Check for path separators
        if "/" in dirname or "\\" in dirname:
            return False

        # Check for forbidden names
        if dirname.lower() in {name.lower() for name in self.FORBIDDEN_FILENAMES}:
            return False

        # Check for hidden directories
        if dirname.startswith("."):
            return False

        # Check length
        if len(dirname) > 100:
            return False

        return True

    def get_security_summary(self) -> Dict[str, Any]:
        """Get summary of security validation rules."""
        return {
            "approved_directory": str(self.approved_directory),
            "allowed_extensions": sorted(list(self.ALLOWED_EXTENSIONS)),
            "forbidden_filenames": sorted(list(self.FORBIDDEN_FILENAMES)),
            "dangerous_patterns_count": len(self.DANGEROUS_PATTERNS),
            "dangerous_file_patterns_count": len(self.DANGEROUS_FILE_PATTERNS),
            "max_filename_length": 255,
            "max_command_length": 1000,
        }
