"""Pydantic schemas for Amplifier agents."""

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from .schema import ModuleConfig


class AgentMetadata(BaseModel):
    """Agent metadata and identification."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique agent identifier")
    description: str = Field(..., description="Human-readable description of agent purpose")


# Backward compatibility alias
AgentMeta = AgentMetadata


class SystemConfig(BaseModel):
    """System instruction configuration."""

    model_config = ConfigDict(frozen=True)

    instruction: str = Field(..., description="System instruction text")


class AgentTools(BaseModel):
    """Agent tool configuration."""

    model_config = ConfigDict(frozen=True)

    providers: list[ModuleConfig] = Field(default_factory=list, description="Provider module overrides")
    tools: list[ModuleConfig] = Field(default_factory=list, description="Tool module overrides")
    hooks: list[ModuleConfig] = Field(default_factory=list, description="Hook module overrides")


class Agent(BaseModel):
    """Complete agent specification - partial mount plan.

    Agents are simpler than profiles:
    - No inheritance (no extends field)
    - No overlays across layers (first-match-wins resolution)
    - Just configuration overlays applied to parent sessions
    """

    model_config = ConfigDict(frozen=True)

    meta: AgentMetadata = Field(..., description="Agent metadata")

    # Module lists - use same ModuleConfig as profiles
    providers: list[ModuleConfig] = Field(default_factory=list, description="Provider module overrides")
    tools: list[ModuleConfig] = Field(default_factory=list, description="Tool module overrides")
    hooks: list[ModuleConfig] = Field(default_factory=list, description="Hook module overrides")

    # Session config overrides
    session: dict[str, Any] | None = Field(None, description="Session configuration overrides")

    # System instruction
    system: SystemConfig | None = Field(None, description="System instruction configuration")

    def to_mount_plan_fragment(self) -> dict[str, Any]:
        """Convert agent to partial mount plan dict (configuration only).

        Mount plans contain only runtime configuration, not metadata.
        The task tool constructs agent names from dictionary keys, not from
        a 'name' field in the config. Only 'description' is needed for display.

        Returns:
            Partial mount plan that can be merged with parent config
        """
        result: dict[str, Any] = {}

        # Description is part of mount plan spec (used by task tool for display)
        result["description"] = self.meta.description

        # Add module lists if present (config overlays)
        if self.providers:
            result["providers"] = [p.model_dump() for p in self.providers]
        if self.tools:
            result["tools"] = [t.model_dump() for t in self.tools]
        if self.hooks:
            result["hooks"] = [h.model_dump() for h in self.hooks]

        # Add session overrides if present
        if self.session:
            result["session"] = self.session

        # Add system instruction if present
        if self.system:
            result["system"] = {"instruction": self.system.instruction}

        return result
