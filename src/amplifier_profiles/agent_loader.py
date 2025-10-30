"""Agent loader for discovering and loading agent files."""

from .agent_resolver import AgentResolver
from .agent_schema import Agent
from .exceptions import AgentNotFoundError
from .exceptions import ProfileError
from .protocols import MentionLoaderProtocol
from .utils import parse_frontmatter
from .utils import parse_markdown_body


class AgentLoader:
    """Discovers and loads Amplifier agents from multiple search paths."""

    def __init__(
        self,
        resolver: AgentResolver | None = None,
        mention_loader: MentionLoaderProtocol | None = None,
    ):
        """
        Initialize agent loader.

        Args:
            resolver: Optional agent resolver. If None, must be provided later
            mention_loader: Optional mention loader for @mention processing
        """
        self.resolver = resolver
        self.mention_loader = mention_loader

    def list_agents(self) -> list[str]:
        """
        Discover all available agent names.

        Returns:
            List of agent names (without .md extension)
        """
        if not self.resolver:
            return []
        return self.resolver.list_agents()

    def load_agent(self, name: str) -> Agent:
        """
        Load an agent configuration from file.

        Args:
            name: Agent name (without .md extension)

        Returns:
            Loaded and validated agent

        Raises:
            AgentNotFoundError: If agent not found
            ProfileError: If agent file is invalid
        """
        if not self.resolver:
            raise ProfileError("Agent resolver not configured")

        agent_file = self.resolver.resolve(name)
        if agent_file is None:
            raise AgentNotFoundError(f"Agent '{name}' not found in search paths")

        try:
            # Parse frontmatter (parse functions expect str content, not Path)
            content = agent_file.read_text()
            data, _ = parse_frontmatter(content)  # Unpack tuple: (frontmatter_dict, body)
            markdown_body = parse_markdown_body(content)

            # Process @mentions in markdown body if mention loader available
            if markdown_body and self.mention_loader and self.mention_loader.has_mentions(markdown_body):
                context_messages = self.mention_loader.load_mentions(markdown_body, relative_to=agent_file.parent)

                # Prepend loaded context to markdown body
                if context_messages:
                    context_parts = []
                    for msg in context_messages:
                        if isinstance(msg.content, str):
                            context_parts.append(msg.content)
                        elif isinstance(msg.content, list):
                            text_parts = []
                            for block in msg.content:
                                if hasattr(block, "text"):
                                    text_parts.append(block.text)  # type: ignore[attr-defined]
                                else:
                                    text_parts.append(str(block))
                            context_parts.append("".join(text_parts))
                        else:
                            context_parts.append(str(msg.content))

                    context_content = "\n\n".join(context_parts)
                    markdown_body = f"{context_content}\n\n{markdown_body}"

            # Add markdown body as system instruction if present and not already defined
            if markdown_body:
                if "system" not in data:
                    data["system"] = {}
                if "instruction" not in data.get("system", {}):
                    data["system"]["instruction"] = markdown_body

            # Handle backward compatibility: old agents have name/description at top level
            if "meta" not in data:
                data["meta"] = {}
                if "name" in data:
                    data["meta"]["name"] = data.pop("name")
                else:
                    data["meta"]["name"] = name

                if "description" in data:
                    data["meta"]["description"] = data.pop("description")
                else:
                    data["meta"]["description"] = f"Agent: {name}"

            # Validate with Pydantic
            agent = Agent(**data)
            return agent

        except Exception as e:
            raise ProfileError(f"Invalid agent file {agent_file}: {e}") from e

    def get_agent_source(self, name: str) -> str | None:
        """
        Determine which source an agent comes from.

        Args:
            name: Agent name

        Returns:
            "bundled", "project", "user", "env", or None if not found
        """
        if not self.resolver:
            return None
        return self.resolver.get_agent_source(name)

    def load_agents_by_names(self, names: list[str]) -> dict[str, dict]:
        """
        Load multiple agents by name.

        Args:
            names: List of agent names to load

        Returns:
            Dict of {agent_name: mount_plan_fragment}
        """
        agents = {}

        for name in names:
            try:
                agent = self.load_agent(name)
                agents[name] = agent.to_mount_plan_fragment()
            except Exception:
                # Skip agents that fail to load
                pass

        return agents
