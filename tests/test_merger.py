"""Tests for profile merging utilities."""

from amplifier_profiles.merger import apply_exclusions
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


class TestApplyExclusions:
    """Test selective inheritance via exclusions."""

    def test_no_exclusions(self):
        """Empty exclusions leave inherited config unchanged."""
        inherited = {"tools": [{"module": "tool-bash"}], "hooks": [{"module": "hooks-logging"}]}
        result = apply_exclusions(inherited, {})
        assert result == inherited

    def test_exclude_all_tools(self):
        """'all' excludes entire section."""
        inherited = {
            "tools": [{"module": "tool-bash"}, {"module": "tool-web"}],
            "hooks": [{"module": "hooks-logging"}],
        }
        result = apply_exclusions(inherited, {"tools": "all"})

        assert result["tools"] == []
        assert len(result["hooks"]) == 1  # Hooks untouched

    def test_exclude_all_hooks(self):
        """'all' works for hooks section."""
        inherited = {"hooks": [{"module": "hooks-logging"}, {"module": "hooks-redaction"}]}
        result = apply_exclusions(inherited, {"hooks": "all"})

        assert result["hooks"] == []

    def test_exclude_all_providers(self):
        """'all' works for providers section."""
        inherited = {"providers": [{"module": "provider-anthropic"}]}
        result = apply_exclusions(inherited, {"providers": "all"})

        assert result["providers"] == []

    def test_exclude_all_agents(self):
        """'all' clears agents dict."""
        inherited = {"agents": {"dirs": ["./agents/"], "include": ["agent-one"]}}
        result = apply_exclusions(inherited, {"agents": "all"})

        assert result["agents"] == {}

    def test_exclude_specific_tools_by_module_id(self):
        """List excludes specific modules by ID."""
        inherited = {
            "tools": [{"module": "tool-bash"}, {"module": "tool-web"}, {"module": "tool-filesystem"}],
        }
        result = apply_exclusions(inherited, {"tools": ["tool-bash", "tool-filesystem"]})

        assert len(result["tools"]) == 1
        assert result["tools"][0]["module"] == "tool-web"

    def test_exclude_specific_hooks_by_module_id(self):
        """List excludes specific hooks by ID."""
        inherited = {
            "hooks": [{"module": "hooks-logging"}, {"module": "hooks-redaction"}, {"module": "hooks-approval"}],
        }
        result = apply_exclusions(inherited, {"hooks": ["hooks-logging"]})

        assert len(result["hooks"]) == 2
        module_ids = {h["module"] for h in result["hooks"]}
        assert module_ids == {"hooks-redaction", "hooks-approval"}

    def test_exclude_nonexistent_module_no_error(self):
        """Excluding nonexistent module doesn't error."""
        inherited = {"tools": [{"module": "tool-bash"}]}
        result = apply_exclusions(inherited, {"tools": ["tool-nonexistent"]})

        assert len(result["tools"]) == 1
        assert result["tools"][0]["module"] == "tool-bash"

    def test_exclude_nonexistent_section_no_error(self):
        """Excluding nonexistent section doesn't error."""
        inherited = {"tools": [{"module": "tool-bash"}]}
        result = apply_exclusions(inherited, {"hooks": "all"})

        assert "tools" in result
        assert len(result["tools"]) == 1

    def test_exclude_nested_agents_dirs(self):
        """Nested dict excludes specific agent dirs."""
        inherited = {"agents": {"dirs": ["./agents/", "./custom-agents/", "./external/"]}}
        result = apply_exclusions(inherited, {"agents": {"dirs": ["./external/"]}})

        assert result["agents"]["dirs"] == ["./agents/", "./custom-agents/"]

    def test_exclude_nested_agents_include(self):
        """Nested dict excludes specific agent includes."""
        inherited = {"agents": {"include": ["agent-one", "agent-two", "agent-three"]}}
        result = apply_exclusions(inherited, {"agents": {"include": ["agent-two"]}})

        assert result["agents"]["include"] == ["agent-one", "agent-three"]

    def test_exclude_nested_all(self):
        """Nested 'all' clears specific nested field."""
        inherited = {"agents": {"dirs": ["./agents/"], "include": ["agent-one"]}}
        result = apply_exclusions(inherited, {"agents": {"dirs": "all"}})

        assert result["agents"]["dirs"] == []
        assert result["agents"]["include"] == ["agent-one"]

    def test_exclude_multiple_sections(self):
        """Multiple exclusions applied together."""
        inherited = {
            "tools": [{"module": "tool-bash"}, {"module": "tool-web"}],
            "hooks": [{"module": "hooks-logging"}],
            "providers": [{"module": "provider-anthropic"}],
        }
        result = apply_exclusions(
            inherited,
            {"tools": "all", "hooks": ["hooks-logging"], "providers": ["provider-anthropic"]},
        )

        assert result["tools"] == []
        assert result["hooks"] == []
        assert result["providers"] == []

    def test_exclude_other_section_removes_entirely(self):
        """Non-standard sections are removed entirely with 'all'."""
        inherited = {"custom": {"setting": "value"}}
        result = apply_exclusions(inherited, {"custom": "all"})

        assert "custom" not in result


class TestMergeProfileDictsWithExclusions:
    """Test merge_profile_dicts with exclusion support."""

    def test_exclude_not_propagated_to_result(self):
        """Exclusions are applied but not included in merged result."""
        parent = {"tools": [{"module": "tool-bash"}]}
        child = {"exclude": {"tools": "all"}}
        result = merge_profile_dicts(parent, child)

        assert "exclude" not in result

    def test_exclude_all_tools_then_add_new(self):
        """Exclude all parent tools, then add child's tools."""
        parent = {"tools": [{"module": "tool-bash", "source": "git+bash"}, {"module": "tool-web", "source": "git+web"}]}
        child = {"exclude": {"tools": "all"}, "tools": [{"module": "tool-filesystem", "source": "git+fs"}]}
        result = merge_profile_dicts(parent, child)

        # Parent tools excluded, only child tool remains
        assert len(result["tools"]) == 1
        assert result["tools"][0]["module"] == "tool-filesystem"

    def test_exclude_specific_hooks_keep_others(self):
        """Exclude specific hooks, keep others, add new ones."""
        parent = {
            "hooks": [
                {"module": "hooks-logging", "source": "git+logging", "config": {"level": "INFO"}},
                {"module": "hooks-redaction", "source": "git+redaction"},
            ]
        }
        child = {
            "exclude": {"hooks": ["hooks-redaction"]},
            "hooks": [{"module": "hooks-approval", "source": "git+approval"}],
        }
        result = merge_profile_dicts(parent, child)

        # hooks-redaction excluded, hooks-logging inherited, hooks-approval added
        assert len(result["hooks"]) == 2
        module_ids = {h["module"] for h in result["hooks"]}
        assert module_ids == {"hooks-logging", "hooks-approval"}

    def test_exclude_specific_then_merge_with_same_module(self):
        """Exclude specific module, then merge child's version of same module."""
        parent = {"tools": [{"module": "tool-bash", "source": "git+old", "config": {"old": True}}]}
        child = {
            "exclude": {"tools": ["tool-bash"]},
            "tools": [{"module": "tool-bash", "source": "git+new", "config": {"new": True}}],
        }
        result = merge_profile_dicts(parent, child)

        # Parent's tool-bash excluded, child's version used (no merge)
        assert len(result["tools"]) == 1
        assert result["tools"][0]["source"] == "git+new"
        assert result["tools"][0]["config"] == {"new": True}

    def test_exclude_all_providers_start_fresh(self):
        """Exclude all parent providers and define entirely new set."""
        parent = {
            "providers": [
                {"module": "provider-anthropic", "source": "git+anthropic"},
                {"module": "provider-openai", "source": "git+openai"},
            ]
        }
        child = {
            "exclude": {"providers": "all"},
            "providers": [{"module": "provider-ollama", "source": "git+ollama"}],
        }
        result = merge_profile_dicts(parent, child)

        assert len(result["providers"]) == 1
        assert result["providers"][0]["module"] == "provider-ollama"

    def test_exclude_nested_agents_dirs(self):
        """Exclude specific agent directories via nested exclusion."""
        parent = {"agents": {"dirs": ["./agents/", "./inherited-agents/"], "include": ["agent-one"]}}
        child = {"exclude": {"agents": {"dirs": ["./inherited-agents/"]}}}
        result = merge_profile_dicts(parent, child)

        assert result["agents"]["dirs"] == ["./agents/"]
        assert result["agents"]["include"] == ["agent-one"]

    def test_complex_exclusion_scenario(self):
        """Complex realistic exclusion scenario."""
        parent = {
            "profile": {"name": "base"},
            "session": {"orchestrator": {"module": "loop-basic"}},
            "tools": [
                {"module": "tool-bash", "source": "git+bash"},
                {"module": "tool-web", "source": "git+web"},
                {"module": "tool-filesystem", "source": "git+fs"},
            ],
            "hooks": [
                {"module": "hooks-logging", "source": "git+logging"},
                {"module": "hooks-redaction", "source": "git+redaction"},
            ],
            "agents": {"dirs": ["./agents/", "./inherited/"]},
        }

        child = {
            "profile": {"name": "production"},
            "exclude": {
                "tools": ["tool-bash"],  # Remove bash for security
                "hooks": ["hooks-logging"],  # Use different logging in prod
                "agents": {"dirs": ["./inherited/"]},  # Don't inherit these agents
            },
            "hooks": [{"module": "hooks-production-logging", "source": "git+prod-logging"}],
        }

        result = merge_profile_dicts(parent, child)

        # Profile metadata from child
        assert result["profile"]["name"] == "production"

        # Session inherited
        assert result["session"]["orchestrator"]["module"] == "loop-basic"

        # Tools: tool-bash excluded, others inherited
        assert len(result["tools"]) == 2
        tool_ids = {t["module"] for t in result["tools"]}
        assert tool_ids == {"tool-web", "tool-filesystem"}

        # Hooks: hooks-logging excluded, redaction inherited, prod-logging added
        assert len(result["hooks"]) == 2
        hook_ids = {h["module"] for h in result["hooks"]}
        assert hook_ids == {"hooks-redaction", "hooks-production-logging"}

        # Agents: inherited/ dir excluded
        assert result["agents"]["dirs"] == ["./agents/"]

    def test_no_exclusions_normal_merge(self):
        """Without exclusions, normal merge behavior unchanged."""
        parent = {"tools": [{"module": "tool-bash", "source": "git+bash"}]}
        child = {"tools": [{"module": "tool-bash", "config": {"debug": True}}]}
        result = merge_profile_dicts(parent, child)

        # Normal merge: source inherited, config added
        assert len(result["tools"]) == 1
        assert result["tools"][0]["source"] == "git+bash"
        assert result["tools"][0]["config"] == {"debug": True}
