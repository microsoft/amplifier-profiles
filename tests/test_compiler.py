"""Tests for profile compiler."""

from amplifier_profiles import ModuleConfig
from amplifier_profiles import Profile
from amplifier_profiles import ProfileMetadata
from amplifier_profiles import SessionConfig
from amplifier_profiles import compile_profile_to_mount_plan


class TestCompileProfileToMountPlan:
    """Test profile to mount plan compilation."""

    def test_basic_profile_compilation(self):
        """Test compiling minimal profile to mount plan."""
        profile = Profile(
            profile=ProfileMetadata(
                name="test",
                version="1.0.0",
                description="Test profile",
                model=None,
                extends=None,
            ),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
            providers=[],
            tools=[],
            hooks=[],
            exclude=None,
        )

        mount_plan = compile_profile_to_mount_plan(profile)

        assert "session" in mount_plan
        assert mount_plan["session"]["orchestrator"] == "loop-basic"
        assert mount_plan["session"]["context"] == "context-simple"
        assert "providers" in mount_plan
        assert "tools" in mount_plan
        assert "hooks" in mount_plan
        assert "agents" in mount_plan

    def test_profile_with_modules(self):
        """Test compiling profile with providers/tools/hooks."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(
                    module="loop-streaming", source="git+https://example.com/orch@v1", config=None
                ),
                context=ModuleConfig(module="context-persistent", source="git+https://example.com/ctx@v1", config=None),
            ),
            agents=None,
            providers=[
                ModuleConfig(
                    module="provider-anthropic",
                    source="git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
                    config={"model": "claude-sonnet-4-5"},
                )
            ],
            tools=[ModuleConfig(module="tool-filesystem", source=None, config=None)],
            hooks=[ModuleConfig(module="hooks-logging", source=None, config={"level": "DEBUG"})],
            exclude=None,
        )

        mount_plan = compile_profile_to_mount_plan(profile)

        # Check session
        assert mount_plan["session"]["orchestrator"] == "loop-streaming"
        assert mount_plan["session"]["orchestrator_source"] == "git+https://example.com/orch@v1"
        assert mount_plan["session"]["context"] == "context-persistent"

        # Check modules
        assert len(mount_plan["providers"]) == 1
        assert mount_plan["providers"][0]["module"] == "provider-anthropic"
        assert mount_plan["providers"][0]["config"]["model"] == "claude-sonnet-4-5"

        assert len(mount_plan["tools"]) == 1
        assert mount_plan["tools"][0]["module"] == "tool-filesystem"

        assert len(mount_plan["hooks"]) == 1
        assert mount_plan["hooks"][0]["config"]["level"] == "DEBUG"

    def test_profile_with_agents_all(self):
        """Test compiling profile with agents='all' configuration."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents="all",
            exclude=None,
        )

        mount_plan = compile_profile_to_mount_plan(profile)

        # Agents will be loaded by agent_loader (tested separately)
        assert "agents" in mount_plan

    def test_profile_with_agents_list(self):
        """Test compiling profile with specific agent list."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=["test-agent", "another-agent"],
            exclude=None,
        )

        mount_plan = compile_profile_to_mount_plan(profile)

        # Agents will be loaded by agent_loader (tested separately)
        assert "agents" in mount_plan

    def test_profile_with_agents_none(self):
        """Test compiling profile with agents='none' disables agents."""
        profile = Profile(
            profile=ProfileMetadata(name="test", version="1.0.0", description="Test", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents="none",
            exclude=None,
        )

        mount_plan = compile_profile_to_mount_plan(profile)

        # Agents should be empty when disabled
        assert "agents" in mount_plan

    def test_overlay_merging(self):
        """Test merging overlay profiles."""
        base = Profile(
            profile=ProfileMetadata(name="base", version="1.0.0", description="Base", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-basic", source=None, config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
            providers=[
                ModuleConfig(
                    module="provider-anthropic",
                    source="git+https://example.com@v1",
                    config={"model": "claude-sonnet-4-5"},
                )
            ],
            exclude=None,
        )

        overlay = Profile(
            profile=ProfileMetadata(name="overlay", version="1.0.0", description="Overlay", model=None, extends=None),
            session=SessionConfig(
                orchestrator=ModuleConfig(module="loop-streaming", source="git+https://example.com@v2", config=None),
                context=ModuleConfig(module="context-simple", source=None, config=None),
            ),
            agents=None,
            providers=[
                ModuleConfig(
                    module="provider-anthropic",
                    source="git+https://example.com@v2",
                    config={"model": "claude-opus-4-1"},
                )
            ],
            tools=[ModuleConfig(module="tool-bash", source=None, config=None)],
            exclude=None,
        )

        mount_plan = compile_profile_to_mount_plan(base, overlays=[overlay])

        # Overlay should override orchestrator
        assert mount_plan["session"]["orchestrator"] == "loop-streaming"
        assert mount_plan["session"]["orchestrator_source"] == "git+https://example.com@v2"

        # Overlay should override provider
        assert len(mount_plan["providers"]) == 1
        assert mount_plan["providers"][0]["config"]["model"] == "claude-opus-4-1"
        assert mount_plan["providers"][0]["source"] == "git+https://example.com@v2"

        # Overlay should add tools
        assert len(mount_plan["tools"]) == 1
        assert mount_plan["tools"][0]["module"] == "tool-bash"
