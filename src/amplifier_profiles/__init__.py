"""Amplifier Profiles - Profile and agent loading system."""

from .agent_loader import AgentLoader
from .agent_resolver import AgentResolver
from .agent_schema import Agent
from .agent_schema import AgentMeta
from .agent_schema import AgentTools
from .agent_schema import SystemConfig
from .compiler import compile_profile_to_mount_plan
from .exceptions import AgentError
from .exceptions import AgentNotFoundError
from .exceptions import ProfileError
from .exceptions import ProfileNotFoundError
from .loader import ProfileLoader
from .merger import merge_dicts
from .merger import merge_module_items
from .merger import merge_module_lists
from .merger import merge_profile_dicts
from .protocols import CollectionResolverProtocol
from .protocols import MentionLoaderProtocol
from .schema import ModuleConfig
from .schema import Profile
from .schema import ProfileMetadata
from .schema import SessionConfig
from .utils import parse_frontmatter
from .utils import parse_markdown_body

__all__ = [
    # Core loading
    "ProfileLoader",
    "AgentLoader",
    "AgentResolver",
    # Compilation
    "compile_profile_to_mount_plan",
    # Merging utilities
    "merge_profile_dicts",
    "merge_module_lists",
    "merge_module_items",
    "merge_dicts",
    # Parsing utilities
    "parse_frontmatter",
    "parse_markdown_body",
    # Schemas
    "Profile",
    "ProfileMetadata",
    "SessionConfig",
    "ModuleConfig",
    "Agent",
    "AgentMeta",
    "SystemConfig",
    "AgentTools",
    # Protocols
    "CollectionResolverProtocol",
    "MentionLoaderProtocol",
    # Exceptions
    "ProfileError",
    "ProfileNotFoundError",
    "AgentError",
    "AgentNotFoundError",
]

__version__ = "0.1.0"
