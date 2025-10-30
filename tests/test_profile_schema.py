"""Tests for amplifier_profiles.schema module."""

import pytest  # type: ignore
from amplifier_profiles.schema import AgentsConfig
from amplifier_profiles.schema import ModuleConfig
from amplifier_profiles.schema import Profile
from amplifier_profiles.schema import ProfileMetadata
from amplifier_profiles.schema import SessionConfig
from pydantic import ValidationError


class TestProfileMetadata:
    """Tests for ProfileMetadata model."""

    def test_valid_metadata(self):
        """Create metadata with all required fields."""
        meta = ProfileMetadata(
            name="test-profile", version="1.0.0", description="Test profile", model=None, extends=None
        )
        assert meta.name == "test-profile"
        assert meta.version == "1.0.0"
        assert meta.description == "Test profile"
        assert meta.model is None
        assert meta.extends is None

    def test_metadata_with_model(self):
        """Create metadata with model field."""
        meta = ProfileMetadata(
            name="test", version="1.0.0", description="Test", model="anthropic/claude-sonnet-4-5", extends=None
        )
        assert meta.model == "anthropic/claude-sonnet-4-5"

    def test_metadata_with_extends(self):
        """Create metadata with extends field."""
        meta = ProfileMetadata(name="child", version="1.0.0", description="Child", model=None, extends="parent")
        assert meta.extends == "parent"

    def test_metadata_frozen(self):
        """Verify model is immutable."""
        meta = ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None)
        with pytest.raises(ValidationError, match="frozen"):
            meta.name = "changed"

    def test_metadata_missing_name(self):
        """Fail when name is missing."""
        with pytest.raises(ValidationError):
            ProfileMetadata(version="1.0.0", description="Test", model=None, extends=None)  # type: ignore[call-arg]  # Intentionally invalid - testing validation

    def test_metadata_missing_version(self):
        """Fail when version is missing."""
        with pytest.raises(ValidationError):
            ProfileMetadata(name="test", description="Test", model=None, extends=None)  # type: ignore[call-arg]  # Intentionally invalid - testing validation

    def test_metadata_missing_description(self):
        """Fail when description is missing."""
        with pytest.raises(ValidationError):
            ProfileMetadata(name="test", version="1.0.0", model=None, extends=None)  # type: ignore[call-arg]  # Intentionally invalid - testing validation


class TestModuleConfig:
    """Tests for ModuleConfig model."""

    def test_module_basic(self):
        """Create module with just module ID."""
        mod = ModuleConfig(module="provider-anthropic", source=None, config=None)
        assert mod.module == "provider-anthropic"
        assert mod.source is None
        assert mod.config is None

    def test_module_with_string_source(self):
        """Create module with string source."""
        mod = ModuleConfig(
            module="provider-anthropic",
            source="git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
            config=None,
        )
        assert isinstance(mod.source, str)
        assert mod.source.startswith("git+")

    def test_module_with_dict_source(self):
        """Create module with dict source."""
        mod = ModuleConfig(
            module="tool-filesystem",
            source={"git": "https://github.com/microsoft/amplifier-module-tool-filesystem", "tag": "v1.0.0"},
            config=None,
        )
        assert isinstance(mod.source, dict)
        assert mod.source["git"] == "https://github.com/microsoft/amplifier-module-tool-filesystem"

    def test_module_with_config(self):
        """Create module with configuration."""
        mod = ModuleConfig(module="provider-anthropic", source=None, config={"model": "claude-sonnet-4-5"})
        assert mod.config == {"model": "claude-sonnet-4-5"}

    def test_module_to_dict_minimal(self):
        """Convert minimal module to dict."""
        mod = ModuleConfig(module="tool-bash", source=None, config=None)
        result = mod.to_dict()
        assert result == {"module": "tool-bash"}

    def test_module_to_dict_with_source(self):
        """Convert module with source to dict."""
        mod = ModuleConfig(module="tool-bash", source="git+https://example.com", config=None)
        result = mod.to_dict()
        assert result == {"module": "tool-bash", "source": "git+https://example.com"}

    def test_module_to_dict_complete(self):
        """Convert complete module to dict."""
        mod = ModuleConfig(
            module="provider-anthropic",
            source="git+https://example.com",
            config={"model": "claude-opus-4-1"},
        )
        result = mod.to_dict()
        assert result == {
            "module": "provider-anthropic",
            "source": "git+https://example.com",
            "config": {"model": "claude-opus-4-1"},
        }

    def test_module_frozen(self):
        """Verify module is immutable."""
        mod = ModuleConfig(module="tool-bash", source=None, config=None)
        with pytest.raises(ValidationError, match="frozen"):
            mod.module = "changed"


class TestSessionConfig:
    """Tests for SessionConfig model."""

    def test_valid_session_config(self):
        """Create valid session configuration."""
        config = SessionConfig(
            orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
            context=ModuleConfig(module="context-simple", source=None, config=None),
        )
        assert config.orchestrator.module == "loop-basic"
        assert config.context.module == "context-simple"

    def test_session_config_with_module_configs(self):
        """Create session with detailed module configs."""
        config = SessionConfig(
            orchestrator=ModuleConfig(
                module="loop-streaming",
                source="git+https://example.com",
                config={"max_tokens": 8000},
            ),
            context=ModuleConfig(
                module="context-persistent",
                source="git+https://example.com",
                config={"path": "~/.amplifier/context"},
            ),
        )
        assert config.orchestrator.config == {"max_tokens": 8000}
        assert config.context.config == {"path": "~/.amplifier/context"}

    def test_session_config_frozen(self):
        """Verify session config is immutable."""
        config = SessionConfig(
            orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
            context=ModuleConfig(module="context-simple", source=None, config=None),
        )
        with pytest.raises(ValidationError, match="frozen"):
            config.orchestrator = ModuleConfig(module="changed", source=None, config=None)

    def test_session_config_missing_orchestrator(self):
        """Fail when orchestrator is missing."""
        with pytest.raises(ValidationError):
            SessionConfig(context=ModuleConfig(module="context-simple", source=None, config=None))  # type: ignore[call-arg]  # Intentionally invalid - testing validation

    def test_session_config_missing_context(self):
        """Fail when context is missing."""
        with pytest.raises(ValidationError):
            SessionConfig(orchestrator=ModuleConfig(module="loop-basic", source=None, config=None))  # type: ignore[call-arg]  # Intentionally invalid - testing validation


class TestAgentsConfig:
    """Tests for AgentsConfig model."""

    def test_agents_config_empty(self):
        """Create empty agents config."""
        config = AgentsConfig(dirs=None, include=None)
        assert config.dirs is None
        assert config.include is None

    def test_agents_config_with_dirs(self):
        """Create agents config with search directories."""
        config = AgentsConfig(dirs=["~/.amplifier/agents", "./agents"], include=None)
        assert config.dirs == ["~/.amplifier/agents", "./agents"]

    def test_agents_config_with_include(self):
        """Create agents config with include filter."""
        config = AgentsConfig(dirs=None, include=["zen-architect", "bug-hunter"])
        assert config.include == ["zen-architect", "bug-hunter"]

    def test_agents_config_complete(self):
        """Create agents config with all fields."""
        config = AgentsConfig(
            dirs=["./agents"],
            include=["agent-one", "agent-two"],
        )
        assert config.dirs == ["./agents"]
        assert config.include == ["agent-one", "agent-two"]

    def test_agents_config_frozen(self):
        """Verify agents config is immutable."""
        config = AgentsConfig(dirs=["./agents"], include=None)
        with pytest.raises(ValidationError, match="frozen"):
            config.dirs = ["changed"]

    def test_no_inline_field(self):
        """Verify AgentsConfig has no 'inline' field (YAGNI)."""
        config = AgentsConfig(dirs=None, include=None)
        assert not hasattr(config, "inline")


class TestProfile:
    """Tests for Profile model."""

    def test_minimal_profile(self):
        """Create minimal valid profile."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test profile", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
        )
        assert profile.profile.name == "test"
        assert profile.session.orchestrator.module == "loop-basic"
        assert profile.agents is None
        assert profile.providers == []
        assert profile.tools == []
        assert profile.hooks == []

    def test_profile_with_agents(self):
        """Create profile with agents configuration."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=AgentsConfig(dirs=["./agents"], include=["agent-one"]),
        )
        assert profile.agents is not None
        assert profile.agents.dirs == ["./agents"]
        assert profile.agents.include == ["agent-one"]

    def test_profile_with_providers(self):
        """Create profile with provider modules."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
            providers=[
                ModuleConfig(
                    module="provider-anthropic",
                    source="git+https://example.com",
                    config={"model": "claude-sonnet-4-5"},
                )
            ],
        )
        assert len(profile.providers) == 1
        assert profile.providers[0].module == "provider-anthropic"

    def test_profile_with_tools(self):
        """Create profile with tool modules."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
            tools=[
                ModuleConfig(module="tool-filesystem", source=None, config=None),
                ModuleConfig(module="tool-bash", source=None, config=None),
            ],
        )
        assert len(profile.tools) == 2
        assert profile.tools[0].module == "tool-filesystem"

    def test_profile_with_hooks(self):
        """Create profile with hook modules."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
            hooks=[ModuleConfig(module="hooks-logging", source=None, config=None)],
        )
        assert len(profile.hooks) == 1
        assert profile.hooks[0].module == "hooks-logging"

    def test_profile_complete(self):
        """Create profile with all optional fields."""
        profile = Profile(
            profile=ProfileMetadata(
                name="full-profile",
                version="2.0.0",
                description="Complete profile",
                model="anthropic/claude-opus-4-1",
                extends="base-profile",
            ),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-streaming", source=None, config={"max_tokens": 8000}),
                context=ModuleConfig(module="context-persistent", source=None, config={"path": "~/.context"}),
            ),
            agents=AgentsConfig(dirs=["./agents"], include=["zen-architect"]),
            providers=[
                ModuleConfig(module="provider-anthropic", source=None, config={"api_key_env": "ANTHROPIC_API_KEY"})
            ],
            tools=[
                ModuleConfig(module="tool-filesystem", source=None, config=None),
                ModuleConfig(module="tool-bash", source=None, config=None),
            ],
            hooks=[
                ModuleConfig(module="hooks-logging", source=None, config=None),
                ModuleConfig(module="hooks-redaction", source=None, config=None),
            ],
        )
        assert profile.profile.name == "full-profile"
        assert profile.profile.extends == "base-profile"
        assert profile.agents is not None
        assert len(profile.providers) == 1
        assert len(profile.tools) == 2
        assert len(profile.hooks) == 2

    def test_profile_frozen(self):
        """Verify profile is immutable."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
        )
        with pytest.raises(ValidationError, match="frozen"):
            profile.profile = ProfileMetadata(
                name="changed", version="1.0.0", description="Changed", model=None, extends=None
            )

    def test_profile_missing_metadata(self):
        """Fail when profile metadata is missing."""
        with pytest.raises(ValidationError):
            Profile(  # type: ignore[call-arg]  # Intentionally invalid - testing validation
                session=SessionConfig(
                    orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                    context=ModuleConfig(module="context-simple", source=None, config=None),
                ),
                agents=None,
            )

    def test_profile_missing_session(self):
        """Fail when session config is missing."""
        with pytest.raises(ValidationError):
            Profile(  # type: ignore[call-arg]  # Intentionally invalid - testing validation
                profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
                agents=None,
            )

    def test_no_task_field(self):
        """Verify Profile has no 'task' field (YAGNI)."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
        )
        assert not hasattr(profile, "task")

    def test_no_logging_field(self):
        """Verify Profile has no 'logging' field (YAGNI)."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
        )
        assert not hasattr(profile, "logging")

    def test_no_ui_field(self):
        """Verify Profile has no 'ui' field (YAGNI)."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
        )
        assert not hasattr(profile, "ui")
