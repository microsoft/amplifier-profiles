"""Tests verifying ProfileLoader and AgentResolver use metadata names from extract_collection_name_from_path()."""

import tempfile
from pathlib import Path

from amplifier_profiles.agent_loader import AgentLoader
from amplifier_profiles.agent_resolver import AgentResolver
from amplifier_profiles.loader import ProfileLoader


def test_profile_loader_uses_metadata_name_not_directory():
    """Verify ProfileLoader uses metadata name as prefix, not directory name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Create collection with mismatched names
        # Directory: amplifier-collection-test
        # Metadata: test-collection
        collection_dir = base / "collections" / "amplifier-collection-test"
        profiles_dir = collection_dir / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create pyproject.toml with metadata name
        (collection_dir / "pyproject.toml").write_text(
            """[project]
name = "test-collection"
version = "1.0.0"
"""
        )

        # Create profile
        (profiles_dir / "designer.md").write_text(
            """---
name: designer
---

# Test profile
"""
        )

        # Load profiles
        loader = ProfileLoader(search_paths=[profiles_dir])
        profiles = loader.list_profiles()

        # Should use metadata name as prefix, not directory name
        assert "test-collection:designer" in profiles
        assert "amplifier-collection-test:designer" not in profiles


def test_agent_resolver_uses_metadata_name_not_directory():
    """Verify AgentResolver uses metadata name as prefix, not directory name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Create collection with mismatched names
        collection_dir = base / "collections" / "amplifier-collection-test"
        agents_dir = collection_dir / "agents"
        agents_dir.mkdir(parents=True)

        # Create pyproject.toml with metadata name
        (collection_dir / "pyproject.toml").write_text(
            """[project]
name = "test-collection"
version = "1.0.0"
"""
        )

        # Create agent
        (agents_dir / "analyzer.md").write_text(
            """---
meta:
  name: analyzer
---

# Test agent
"""
        )

        # Load agents
        resolver = AgentResolver(search_paths=[agents_dir])
        agents = resolver.list_agents()

        # Should use metadata name as prefix, not directory name
        assert "test-collection:analyzer" in agents
        assert "amplifier-collection-test:analyzer" not in agents


def test_agent_loader_uses_metadata_prefix():
    """Verify AgentLoader can load agents with metadata-based prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Create collection
        collection_dir = base / "collections" / "repo-name"
        agents_dir = collection_dir / "agents"
        agents_dir.mkdir(parents=True)

        (collection_dir / "pyproject.toml").write_text(
            """[project]
name = "metadata-name"
version = "1.0.0"
"""
        )

        # Create agent file
        (agents_dir / "expert.md").write_text(
            """---
meta:
  name: expert
  description: Test expert
---

You are a test expert.
"""
        )

        # Create collection resolver for loading by prefix
        from amplifier_collections import CollectionResolver

        collection_resolver = CollectionResolver(search_paths=[base / "collections"])

        # Create resolver and loader
        resolver = AgentResolver(search_paths=[agents_dir], collection_resolver=collection_resolver)
        loader = AgentLoader(resolver=resolver)

        # List should show metadata prefix
        agents = loader.list_agents()
        assert "metadata-name:expert" in agents

        # Load by metadata prefix should work
        agent = loader.load_agent("metadata-name:expert")
        assert agent is not None
        assert agent.meta.name == "expert"


def test_nested_structure_uses_metadata_name():
    """Verify nested structure (uv pip install) uses metadata name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Nested structure (as uv creates)
        collection_dir = base / "collections" / "amplifier-collection-design-intelligence"
        package_dir = collection_dir / "design_intelligence"
        profiles_dir = package_dir / "profiles"
        profiles_dir.mkdir(parents=True)

        (package_dir / "pyproject.toml").write_text(
            """[project]
name = "design-intelligence"
version = "1.0.0"
"""
        )

        (profiles_dir / "designer.md").write_text(
            """---
name: designer
---

# Designer profile
"""
        )

        # Load from nested structure
        loader = ProfileLoader(search_paths=[profiles_dir])
        profiles = loader.list_profiles()

        # Should extract from nested pyproject.toml
        assert "design-intelligence:designer" in profiles
        assert "amplifier-collection-design-intelligence:designer" not in profiles
        assert "design_intelligence:designer" not in profiles  # Not package name


def test_hybrid_packaging_uses_metadata_name():
    """Verify hybrid packaging (resources at parent) uses metadata name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Hybrid: resources at collection_dir, pyproject in package subdir
        collection_dir = base / "collections" / "repo-name"
        package_dir = collection_dir / "package_name"
        package_dir.mkdir(parents=True)

        (package_dir / "pyproject.toml").write_text(
            """[project]
name = "metadata-name"
version = "1.0.0"
"""
        )

        # Resources at parent (collection_dir)
        agents_dir = collection_dir / "agents"
        agents_dir.mkdir()

        (agents_dir / "helper.md").write_text(
            """---
meta:
  name: helper
---

# Helper agent
"""
        )

        # Load from hybrid structure
        resolver = AgentResolver(search_paths=[agents_dir])
        agents = resolver.list_agents()

        # Should find pyproject.toml in package subdir and use its metadata
        assert "metadata-name:helper" in agents
        assert "repo-name:helper" not in agents
