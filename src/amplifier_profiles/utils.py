"""Utility functions for parsing profile and agent markdown files."""

import re
from typing import Any

import yaml


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter and markdown body from profile/agent file.

    Args:
        content: Raw file content with YAML frontmatter

    Returns:
        Tuple of (frontmatter_dict, markdown_body)

    Example:
        >>> content = '''---
        ... name: my-profile
        ... ---
        ... Profile description
        ... '''
        >>> fm, body = parse_frontmatter(content)
        >>> fm["name"]
        'my-profile'
        >>> body
        'Profile description'
    """
    # Match YAML frontmatter block (between --- and ---)
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)

    if not match:
        # No frontmatter - return empty dict and full content as body
        return {}, content

    frontmatter_str = match.group(1)
    body = match.group(2).strip()

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    return frontmatter, body


def parse_markdown_body(content: str) -> str:
    """
    Extract markdown body from profile/agent file (content after frontmatter).

    Args:
        content: Raw file content with YAML frontmatter

    Returns:
        Markdown body text

    Example:
        >>> content = '''---
        ... name: my-profile
        ... ---
        ... Profile description
        ... '''
        >>> parse_markdown_body(content)
        'Profile description'
    """
    _, body = parse_frontmatter(content)
    return body
