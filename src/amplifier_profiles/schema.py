"""Pydantic schemas for Amplifier profiles (YAGNI cleaned - no inline/task/logging/ui)."""

from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class ProfileMetadata(BaseModel):
    """Profile metadata and identification."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique profile identifier")
    version: str = Field(..., description="Semantic version (e.g., '1.0.0')")
    description: str = Field(..., description="Human-readable description")
    model: str | None = Field(None, description="Model in 'provider/model' format")
    extends: str | None = Field(None, description="Parent profile to inherit from")


class ModuleConfig(BaseModel):
    """Configuration for a single module."""

    model_config = ConfigDict(frozen=True)

    module: str = Field(..., description="Module ID to load")
    source: str | dict[str, Any] | None = Field(
        None, description="Module source (git URL, file path, or package name). String or object format."
    )
    config: dict[str, Any] | None = Field(None, description="Module-specific configuration")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for Mount Plan."""
        result: dict[str, Any] = {"module": self.module}
        if self.source is not None:
            result["source"] = self.source
        if self.config is not None:
            result["config"] = self.config
        return result


class SessionConfig(BaseModel):
    """Core session configuration."""

    model_config = ConfigDict(frozen=True)

    orchestrator: ModuleConfig = Field(..., description="Orchestrator module configuration")
    context: ModuleConfig = Field(..., description="Context module configuration")


class AgentsConfig(BaseModel):
    """Configuration for agent discovery and filtering (NO inline support - YAGNI removed)."""

    model_config = ConfigDict(frozen=True)

    dirs: list[str] | None = Field(None, description="Directories to search for agent .md files")
    include: list[str] | None = Field(None, description="Specific agents to include (filters discovered agents)")


class Profile(BaseModel):
    """Complete profile specification (YAGNI cleaned - no task/logging/ui fields)."""

    model_config = ConfigDict(frozen=True)

    profile: ProfileMetadata
    session: SessionConfig
    agents: AgentsConfig | None = Field(None, description="Agent discovery and filtering")
    providers: list[ModuleConfig] = Field(default_factory=list)
    tools: list[ModuleConfig] = Field(default_factory=list)
    hooks: list[ModuleConfig] = Field(default_factory=list)
