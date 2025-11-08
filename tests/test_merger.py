"""Tests for profile merging utilities."""

from amplifier_profiles.merger import merge_dicts
from amplifier_profiles.merger import merge_module_items
from amplifier_profiles.merger import merge_module_lists
from amplifier_profiles.merger import merge_profile_dicts


class TestMergeDicts:
    """Test recursive dictionary merging."""

    def test_merge_empty_dicts(self):
        """Empty dicts merge to empty dict."""
        assert merge_dicts({}, {}) == {}

    def test_merge_with_empty_parent(self):
        """Child dict fully appears when parent empty."""
        child = {"a": 1, "b": 2}
        assert merge_dicts({}, child) == child

    def test_merge_with_empty_child(self):
        """Parent dict preserved when child empty."""
        parent = {"a": 1, "b": 2}
        assert merge_dicts(parent, {}) == parent

    def test_child_overrides_scalar(self):
        """Child scalar values override parent scalars."""
        parent = {"a": 1, "b": 2}
        child = {"a": 10}
        result = merge_dicts(parent, child)
        assert result == {"a": 10, "b": 2}

    def test_child_adds_new_keys(self):
        """Child can add keys not in parent."""
        parent = {"a": 1}
        child = {"b": 2, "c": 3}
        result = merge_dicts(parent, child)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_recursive_merge_nested_dicts(self):
        """Nested dicts are recursively merged."""
        parent = {"a": {"x": 1, "y": 2}, "b": 3}
        child = {"a": {"x": 10, "z": 4}}
        result = merge_dicts(parent, child)
        assert result == {"a": {"x": 10, "y": 2, "z": 4}, "b": 3}

    def test_deep_nesting_merge(self):
        """Deep nesting levels are handled correctly."""
        parent = {"a": {"b": {"c": {"d": 1}}}}
        child = {"a": {"b": {"c": {"e": 2}}}}
        result = merge_dicts(parent, child)
        assert result == {"a": {"b": {"c": {"d": 1, "e": 2}}}}

    def test_list_override_not_merge(self):
        """Lists override, don't merge element-wise."""
        parent = {"items": [1, 2, 3]}
        child = {"items": [4, 5]}
        result = merge_dicts(parent, child)
        assert result == {"items": [4, 5]}

    def test_type_change_child_wins(self):
        """Type changes result in child value being used."""
        parent = {"value": {"nested": "dict"}}
        child = {"value": "scalar"}
        result = merge_dicts(parent, child)
        assert result == {"value": "scalar"}


class TestMergeModuleItems:
    """Test merging of individual module items."""

    def test_merge_with_config_deep_merge(self):
        """Config dicts are deep-merged."""
        parent = {"module": "A", "source": "git+...", "config": {"x": 1, "y": 2}}
        child = {"module": "A", "config": {"y": 20, "z": 3}}
        result = merge_module_items(parent, child)

        assert result["module"] == "A"
        assert result["source"] == "git+..."
        assert result["config"] == {"x": 1, "y": 20, "z": 3}

    def test_source_inherited_when_not_in_child(self):
        """Source field is inherited from parent."""
        parent = {"module": "hooks-status", "source": "git+https://example.com/hook@main"}
        child = {"module": "hooks-status", "config": {"debug": True}}
        result = merge_module_items(parent, child)

        assert result["source"] == "git+https://example.com/hook@main"
        assert result["config"] == {"debug": True}

    def test_source_override_when_in_child(self):
        """Child can override source if explicitly provided."""
        parent = {"module": "A", "source": "git+parent"}
        child = {"module": "A", "source": "git+child"}
        result = merge_module_items(parent, child)

        assert result["source"] == "git+child"

    def test_config_only_in_parent(self):
        """Config from parent preserved when child has none."""
        parent = {"module": "A", "config": {"x": 1}}
        child = {"module": "A"}
        result = merge_module_items(parent, child)

        assert result["config"] == {"x": 1}

    def test_config_only_in_child(self):
        """Config from child used when parent has none."""
        parent = {"module": "A", "source": "git+..."}
        child = {"module": "A", "config": {"x": 1}}
        result = merge_module_items(parent, child)

        assert result["config"] == {"x": 1}

    def test_arbitrary_fields_merged(self):
        """Other fields besides config/source are handled."""
        parent = {"module": "A", "custom": "parent-value"}
        child = {"module": "A", "custom": "child-value", "new": "field"}
        result = merge_module_items(parent, child)

        assert result["custom"] == "child-value"
        assert result["new"] == "field"


class TestMergeModuleLists:
    """Test merging of module lists by module ID."""

    def test_merge_empty_lists(self):
        """Empty lists merge to empty list."""
        assert merge_module_lists([], []) == []

    def test_parent_only_modules_preserved(self):
        """Modules only in parent are preserved."""
        parent = [{"module": "A", "source": "git+A"}, {"module": "B", "source": "git+B"}]
        child = []
        result = merge_module_lists(parent, child)

        assert len(result) == 2
        assert any(m["module"] == "A" for m in result)
        assert any(m["module"] == "B" for m in result)

    def test_child_only_modules_added(self):
        """Modules only in child are added."""
        parent = [{"module": "A"}]
        child = [{"module": "B"}, {"module": "C"}]
        result = merge_module_lists(parent, child)

        assert len(result) == 3
        module_ids = {m["module"] for m in result}
        assert module_ids == {"A", "B", "C"}

    def test_same_module_deep_merged(self):
        """Module appearing in both lists is deep-merged."""
        parent = [{"module": "hooks-status", "source": "git+...", "config": {"a": 1}}]
        child = [{"module": "hooks-status", "config": {"b": 2}}]
        result = merge_module_lists(parent, child)

        assert len(result) == 1
        assert result[0]["module"] == "hooks-status"
        assert result[0]["source"] == "git+..."
        assert result[0]["config"] == {"a": 1, "b": 2}

    def test_multiple_modules_with_overlap(self):
        """Mix of overlapping and unique modules handled correctly."""
        parent = [
            {"module": "A", "source": "git+A"},
            {"module": "B", "source": "git+B", "config": {"x": 1}},
        ]
        child = [
            {"module": "B", "config": {"y": 2}},  # Overlaps with parent
            {"module": "C", "source": "git+C"},  # New in child
        ]
        result = merge_module_lists(parent, child)

        assert len(result) == 3
        module_map = {m["module"]: m for m in result}

        # Module A preserved from parent
        assert module_map["A"]["source"] == "git+A"

        # Module B merged
        assert module_map["B"]["source"] == "git+B"
        assert module_map["B"]["config"] == {"x": 1, "y": 2}

        # Module C added from child
        assert module_map["C"]["source"] == "git+C"

    def test_module_without_id_skipped(self):
        """Modules without 'module' field are skipped (defensive)."""
        parent = [{"module": "A"}]
        child = [{"source": "git+..."}]  # No 'module' field
        result = merge_module_lists(parent, child)

        # Only module A should be present
        assert len(result) == 1
        assert result[0]["module"] == "A"


class TestMergeProfileDicts:
    """Test complete profile dictionary merging."""

    def test_merge_empty_profiles(self):
        """Empty profiles merge to empty profile."""
        assert merge_profile_dicts({}, {}) == {}

    def test_scalar_fields_override(self):
        """Scalar profile fields override."""
        parent = {"profile": {"name": "parent", "version": "1.0.0"}}
        child = {"profile": {"name": "child", "version": "2.0.0"}}
        result = merge_profile_dicts(parent, child)

        assert result["profile"]["name"] == "child"
        assert result["profile"]["version"] == "2.0.0"

    def test_hooks_list_merged(self):
        """Hooks list is merged by module ID."""
        parent = {"hooks": [{"module": "hooks-logging", "source": "git+logging", "config": {"mode": "session"}}]}
        child = {"hooks": [{"module": "hooks-logging", "config": {"verbose": True}}]}
        result = merge_profile_dicts(parent, child)

        assert len(result["hooks"]) == 1
        hook = result["hooks"][0]
        assert hook["source"] == "git+logging"
        assert hook["config"] == {"mode": "session", "verbose": True}

    def test_tools_list_merged(self):
        """Tools list is merged by module ID."""
        parent = {"tools": [{"module": "tool-web", "source": "git+web"}]}
        child = {"tools": [{"module": "tool-bash", "source": "git+bash"}]}
        result = merge_profile_dicts(parent, child)

        assert len(result["tools"]) == 2
        module_ids = {t["module"] for t in result["tools"]}
        assert module_ids == {"tool-web", "tool-bash"}

    def test_providers_list_merged(self):
        """Providers list is merged by module ID."""
        parent = {"providers": [{"module": "provider-anthropic", "source": "git+anthropic", "config": {}}]}
        child = {"providers": [{"module": "provider-anthropic", "config": {"debug": True}}]}
        result = merge_profile_dicts(parent, child)

        assert len(result["providers"]) == 1
        provider = result["providers"][0]
        assert provider["source"] == "git+anthropic"
        assert provider["config"]["debug"] is True

    def test_session_dict_deep_merged(self):
        """Session dict is recursively deep-merged."""
        parent = {
            "session": {
                "orchestrator": {"module": "loop-streaming", "source": "git+streaming"},
                "max_tokens": 100000,
            }
        }
        child = {"session": {"context": {"module": "context-simple"}, "max_tokens": 150000}}
        result = merge_profile_dicts(parent, child)

        # Orchestrator inherited from parent
        assert result["session"]["orchestrator"]["module"] == "loop-streaming"
        assert result["session"]["orchestrator"]["source"] == "git+streaming"

        # Context added from child
        assert result["session"]["context"]["module"] == "context-simple"

        # max_tokens overridden by child
        assert result["session"]["max_tokens"] == 150000

    def test_complex_realistic_merge(self):
        """Complex realistic profile merge scenario."""
        parent = {
            "profile": {"name": "base", "version": "1.0.0"},
            "session": {
                "orchestrator": {"module": "loop-basic", "source": "git+basic"},
                "context": {"module": "context-simple", "source": "git+simple"},
                "max_tokens": 100000,
            },
            "tools": [{"module": "tool-filesystem", "source": "git+fs"}],
            "hooks": [
                {"module": "hooks-logging", "source": "git+logging", "config": {"mode": "session"}},
                {"module": "hooks-redaction", "source": "git+redaction"},
            ],
        }

        child = {
            "profile": {"name": "dev", "version": "2.0.0", "extends": "base"},
            "session": {
                "orchestrator": {"module": "loop-streaming", "source": "git+streaming"},
                "max_tokens": 150000,
            },
            "tools": [
                {"module": "tool-bash", "source": "git+bash"},
                {"module": "tool-web", "source": "git+web"},
            ],
            "hooks": [{"module": "hooks-logging", "config": {"verbose": True}}],
        }

        result = merge_profile_dicts(parent, child)

        # Profile metadata from child
        assert result["profile"]["name"] == "dev"
        assert result["profile"]["version"] == "2.0.0"

        # Session: orchestrator overridden, context inherited, max_tokens overridden
        assert result["session"]["orchestrator"]["module"] == "loop-streaming"
        assert result["session"]["context"]["module"] == "context-simple"
        assert result["session"]["context"]["source"] == "git+simple"
        assert result["session"]["max_tokens"] == 150000

        # Tools: parent tool + 2 child tools
        assert len(result["tools"]) == 3
        tool_ids = {t["module"] for t in result["tools"]}
        assert tool_ids == {"tool-filesystem", "tool-bash", "tool-web"}

        # Hooks: logging merged with new config, redaction inherited
        assert len(result["hooks"]) == 2
        hook_map = {h["module"]: h for h in result["hooks"]}

        logging_hook = hook_map["hooks-logging"]
        assert logging_hook["source"] == "git+logging"
        assert logging_hook["config"] == {"mode": "session", "verbose": True}

        redaction_hook = hook_map["hooks-redaction"]
        assert redaction_hook["source"] == "git+redaction"

    def test_child_can_be_partial(self):
        """Child profile can be partial, inheriting required fields from parent."""
        # This is the key use case - child only specifies differences
        parent = {
            "profile": {"name": "base", "version": "1.0.0"},
            "session": {
                "orchestrator": {"module": "loop-basic", "source": "git+basic"},
                "context": {"module": "context-simple", "source": "git+simple"},
            },
            "providers": [{"module": "provider-anthropic", "source": "git+anthropic"}],
        }

        # Child is minimal - only adds hooks
        child = {"hooks": [{"module": "hooks-logging", "source": "git+logging"}]}

        result = merge_profile_dicts(parent, child)

        # All parent fields preserved
        assert "profile" in result
        assert "session" in result
        assert "providers" in result

        # Child's additions present
        assert "hooks" in result
        assert len(result["hooks"]) == 1

        # Session fully inherited
        assert result["session"]["orchestrator"]["module"] == "loop-basic"
        assert result["session"]["context"]["module"] == "context-simple"
