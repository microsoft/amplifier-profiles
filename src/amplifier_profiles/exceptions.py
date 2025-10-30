"""Exception definitions for amplifier-profiles."""


class ProfileError(Exception):
    """Base exception for profile-related errors."""

    def __init__(self, message: str, context: dict | None = None):
        """Initialize profile error with message and optional context.

        Args:
            message: Human-readable error message
            context: Optional dict with error context (paths, names, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ProfileNotFoundError(ProfileError):
    """Raised when a profile cannot be found in search paths."""

    pass


class ProfileValidationError(ProfileError):
    """Raised when profile frontmatter fails validation."""

    pass


class ProfileLoadError(ProfileError):
    """Raised when profile loading fails (I/O, parsing, etc.)."""

    pass


class ProfileCircularInheritanceError(ProfileError):
    """Raised when circular inheritance is detected in profile chain."""

    pass


# Alias for shorter name
CircularInheritanceError = ProfileCircularInheritanceError


class AgentError(Exception):
    """Base exception for agent-related errors."""

    def __init__(self, message: str, context: dict | None = None):
        """Initialize agent error with message and optional context.

        Args:
            message: Human-readable error message
            context: Optional dict with error context (paths, names, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}


class AgentNotFoundError(AgentError):
    """Raised when an agent cannot be found in search paths."""

    pass


class AgentLoadError(AgentError):
    """Raised when agent loading fails (I/O, parsing, etc.)."""

    pass


class AgentValidationError(AgentError):
    """Raised when agent frontmatter fails validation."""

    pass
