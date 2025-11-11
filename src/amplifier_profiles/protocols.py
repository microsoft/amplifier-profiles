"""Protocols for optional dependencies injection."""

from pathlib import Path
from typing import Any
from typing import Protocol


class CollectionResolverProtocol(Protocol):
    """Protocol for resolving collection names to paths.

    This allows amplifier-profiles to support collection syntax
    without depending on amplifier-collections directly.

    Example implementations:
        - CollectionResolver from amplifier-collections
        - Mock implementation for testing
        - None if collections not supported
    """

    def resolve(self, collection_name: str) -> Path | None:
        """Resolve collection name to filesystem path.

        Args:
            collection_name: Collection identifier (e.g., "foundation")

        Returns:
            Path to collection directory, or None if not found

        Example:
            >>> resolver.resolve("foundation")
            Path("/home/user/.amplifier/collections/foundation")
        """
        ...

    def resolve_collection_path(self, collection_name: str) -> Path | None:
        """Alias for resolve() for backward compatibility.

        Args:
            collection_name: Collection identifier (e.g., "foundation")

        Returns:
            Path to collection directory, or None if not found
        """
        ...


class MentionLoaderProtocol(Protocol):
    """Protocol for loading @mention references.

    This allows amplifier-profiles to support @mention expansion
    without depending on specific mention loader implementations.

    Example implementations:
        - MentionLoader from amplifier-app-cli
        - Simplified version for web apps
        - None if @mentions not supported
    """

    def has_mentions(self, text: str) -> bool:
        """Check if text contains @mention patterns.

        Args:
            text: Text to check for @mentions

        Returns:
            True if @mentions found, False otherwise
        """
        ...

    def load_mentions(
        self, text: str, relative_to: Path | None = None, deduplicator: Any | None = None
    ) -> list[Any]:  # Returns list[Message] but we avoid importing Message here
        """Load files referenced in text via @mention syntax.

        Args:
            text: Text containing @mention patterns
            relative_to: Optional base path for relative references
            deduplicator: Optional session-wide ContentDeduplicator for cross-call deduplication

        Returns:
            List of Message objects with loaded content

        Example:
            >>> loader.load_mentions("@user:notes.md", relative_to=Path("."))
            [Message(role="user", content="Content from notes.md")]
        """
        ...
