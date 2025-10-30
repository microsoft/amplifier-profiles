"""Agent file resolver for discovering agent files from multiple search locations."""

import os
from pathlib import Path

from amplifier_collections import extract_collection_name_from_path

from .protocols import CollectionResolverProtocol


class AgentResolver:
    """Resolves agent files from standard search locations using first-match-wins strategy."""

    def __init__(
        self,
        search_paths: list[Path],
        collection_resolver: CollectionResolverProtocol | None = None,
    ):
        """
        Initialize agent resolver.

        Args:
            search_paths: List of paths to search for agents
            collection_resolver: Optional collection resolver for collection:agent syntax
        """
        self.search_paths = search_paths
        self.collection_resolver = collection_resolver

    def resolve(self, agent_name: str) -> Path | None:
        """
        Resolve agent file by name using first-match-wins.

        Supports multiple formats:
        1. Collection with simple name: "developer-expertise:zen-architect" → collection/agents/zen-architect.md
        2. Collection with full path: "developer-expertise:agents/zen-architect.md" → uses exact path
        3. Simple name: "zen-architect" (searches local paths)

        Resolution order for simple names (highest priority first):
        1. Environment variable AMPLIFIER_AGENT_<NAME>
        2. Search paths (in order provided, typically: user → project → bundled)

        Args:
            agent_name: Agent name (simple or collection:path format)

        Returns:
            Path to agent file if found, None otherwise
        """
        # Collection syntax
        if ":" in agent_name:
            if not self.collection_resolver:
                return None

            collection_name, agent_path = agent_name.split(":", 1)
            collection_path = self.collection_resolver.resolve(collection_name)
            if collection_path:
                # Try as full path first
                full_path = collection_path / agent_path
                if full_path.exists() and full_path.is_file():
                    return full_path

                # Try as simple name
                if not agent_path.startswith("agents/"):
                    simple_name = agent_path if agent_path.endswith(".md") else f"{agent_path}.md"
                    full_path = collection_path / "agents" / simple_name
                    if full_path.exists() and full_path.is_file():
                        return full_path

            return None

        # Check environment variable
        env_key = f"AMPLIFIER_AGENT_{agent_name.upper().replace('-', '_')}"
        if env_path := os.getenv(env_key):
            path = Path(env_path)
            if path.exists():
                return path

        # Search standard paths (reverse order = highest priority first)
        for search_path in reversed(self.search_paths):
            agent_file = search_path / f"{agent_name}.md"
            if agent_file.exists():
                return agent_file

        return None

    def list_agents(self) -> list[str]:
        """
        Discover all available agent names from all search paths.

        Returns agent names with collection prefix when from collections:
        - Simple: "zen-architect", "bug-hunter"
        - Collection: "design-intelligence:art-director", "developer-expertise:zen-architect"

        Returns:
            List of agent names
        """
        agents = set()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            for agent_file in search_path.glob("*.md"):
                # Skip README files
                if agent_file.stem.upper() == "README":
                    continue

                agent_name = agent_file.stem

                # Check if this agent is from a collection
                # Per DRY: Use library utility instead of manual parsing
                if "/collections/" in str(search_path):
                    collection_name = extract_collection_name_from_path(search_path)
                    if collection_name:
                        agents.add(f"{collection_name}:{agent_name}")
                    else:
                        # Fallback if extraction fails
                        agents.add(agent_name)
                else:
                    agents.add(agent_name)

        return sorted(agents)

    def get_agent_source(self, name: str) -> str | None:
        """
        Determine which source an agent comes from.

        Args:
            name: Agent name (simple or collection:agent format)

        Returns:
            "bundled", "bundled-collection", "project", "project-collection",
            "user", "user-collection", "env", or None if not found
        """
        # Check env var first
        env_key = f"AMPLIFIER_AGENT_{name.upper().replace('-', '_')}"
        if os.getenv(env_key):
            return "env"

        agent_file = self.resolve(name)
        if agent_file is None:
            return None

        path_str = str(agent_file)

        # Check for collections first
        if "/collections/" in path_str:
            if "amplifier_app_cli" in path_str and "data/collections" in path_str:
                return "bundled"
            if ".amplifier/collections" in path_str and str(Path.home()) not in path_str:
                return "project-collection"
            if str(Path.home()) in path_str and ".amplifier/collections" in path_str:
                return "user-collection"
            return "collection"

        # Non-collection agents
        if str(Path.home()) in path_str and ".amplifier/agents" in path_str:
            return "user"
        if ".amplifier/agents" in path_str:
            return "project"
        if "amplifier_app_cli" in path_str:
            return "bundled"

        return "unknown"
