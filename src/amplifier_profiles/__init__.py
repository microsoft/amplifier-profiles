"""Amplifier Profiles - Profile and agent loading system."""

from .agent_loader import AgentLoader
from .agent_resolver import AgentResolver
from .agent_schema import Agent
from .agent_schema import AgentMeta
from .agent_schema import AgentTools
from .agent_schema import SystemConfig
from .compiler import compile_profile_to_mount_plan
from .exceptions import AgentNotFoundError
from .exceptions import ProfileError
from .exceptions import ProfileNotFoundError
from .loader import ProfileLoader
from .protocols import CollectionResolverProtocol
from .protocols import MentionLoaderProtocol
from .schema import AgentsConfig
from .schema import ModuleConfig
from .schema import Profile
from .schema import ProfileMetadata
from .schema import SessionConfig

__all__ = [
    # Core loading
    "ProfileLoader",
    "AgentLoader",
    "AgentResolver",
    # Compilation
    "compile_profile_to_mount_plan",
    # Schemas
    "Profile",
    "ProfileMetadata",
    "SessionConfig",
    "ModuleConfig",
    "AgentsConfig",
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
    "AgentNotFoundError",
]

__version__ = "0.1.0"
