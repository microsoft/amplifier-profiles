"""Profile merging utilities for inheritance.

This module implements deep merging of profile configurations, allowing child
profiles to be partial and inherit from parent profiles without duplication.

Key principles:
- Module lists (hooks/tools/providers) are merged by module ID
- Config dictionaries are recursively deep-merged
- Sources are inherited - child profiles don't need to repeat git URLs
- Scalars override - simple values in child replace parent values
- Exclusions allow selective inheritance (exclude sections or specific items)
- Agents field: inherits from parent if omitted, can be excluded

This supports the "merge-then-validate" pattern where validation happens
after the complete inheritance chain is merged.

Exclusion syntax:
- `exclude: {tools: all}` - exclude entire tools section from inheritance
- `exclude: {hooks: [hooks-logging, hooks-redaction]}` - exclude specific hooks
- `exclude: {agents: all}` - exclude agents section (disable agents)
- `exclude: {agents: [agent-a, agent-b]}` - exclude specific agents from list
"""

from typing import Any


def apply_exclusions(inherited: dict[str, Any], exclusions: dict[str, Any]) -> dict[str, Any]:
    """
    Apply exclusions to inherited configuration.

    Exclusions remove items from the inherited configuration before merging
    with child additions. This enables selective inheritance.

    Exclusion formats:
    - `section: "all"` - Remove entire section (e.g., `tools: all`, `agents: all`)
    - `section: [list]` - Remove specific items (e.g., `hooks: [hooks-logging]`, `agents: [agent-name]`)

    Args:
        inherited: Configuration inherited from parent (will be modified)
        exclusions: Exclusion rules to apply

    Returns:
        Configuration with exclusions applied

    Example:
        >>> inherited = {
        ...     "tools": [{"module": "tool-bash"}, {"module": "tool-web"}],
        ...     "hooks": [{"module": "hooks-logging"}],
        ... }
        >>> exclusions = {"tools": "all", "hooks": ["hooks-logging"]}
        >>> result = apply_exclusions(inherited, exclusions)
        >>> result["tools"]  # Entire section excluded
        []
        >>> result["hooks"]  # Specific hook excluded
        []
    """
    result = inherited.copy()

    for section, exclusion_value in exclusions.items():
        if section not in result:
            # Section doesn't exist in inherited, nothing to exclude
            continue

        if exclusion_value == "all":
            # Exclude entire section
            result = _apply_exclude_all(result, section)

        elif isinstance(exclusion_value, list):
            # Exclude specific items from a module list
            result = _apply_exclude_list(result, section, exclusion_value)

        elif isinstance(exclusion_value, dict):
            # Nested exclusions for complex sections
            result = _apply_exclude_nested(result, section, exclusion_value)

    return result


def _apply_exclude_all(result: dict[str, Any], section: str) -> dict[str, Any]:
    """Apply 'all' exclusion to a section - removes entire section content."""
    if section in ("tools", "hooks", "providers"):
        result[section] = []
    elif section == "agents":
        # For agents, set to "none" to disable (Smart Single Value format)
        result[section] = "none"
    else:
        # For other sections, remove entirely
        del result[section]
    return result


def _apply_exclude_list(result: dict[str, Any], section: str, exclusion_list: list) -> dict[str, Any]:
    """Apply list exclusion - removes specific items from module lists or agent names."""
    if section in ("tools", "hooks", "providers") and isinstance(result[section], list):
        result[section] = [item for item in result[section] if item.get("module") not in exclusion_list]
    elif section == "agents" and isinstance(result[section], list):
        # For agents (Smart Single Value format), remove specific agent names from list
        result[section] = [agent for agent in result[section] if agent not in exclusion_list]
    return result


def _apply_exclude_nested(result: dict[str, Any], section: str, nested_exclusions: dict) -> dict[str, Any]:
    """Apply nested exclusions for dict-type sections.

    Note: For 'agents' section with Smart Single Value format (str | list[str]),
    nested exclusions don't apply - use 'all' or list exclusions instead.
    """
    # Skip sections that aren't dicts (e.g., agents with Smart Single Value format)
    if not isinstance(result.get(section), dict):
        return result

    section_copy = result[section].copy()
    for nested_key, nested_exclusion in nested_exclusions.items():
        if nested_key not in section_copy:
            continue

        if nested_exclusion == "all":
            # Exclude entire nested field
            if isinstance(section_copy[nested_key], list):
                section_copy[nested_key] = []
            else:
                del section_copy[nested_key]
        elif isinstance(nested_exclusion, list) and isinstance(section_copy[nested_key], list):
            # Exclude specific items from nested list
            section_copy[nested_key] = [item for item in section_copy[nested_key] if item not in nested_exclusion]

    result[section] = section_copy
    return result


def merge_profile_dicts(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge child profile dictionary into parent profile dictionary.

    Merge rules by key:
    - 'exclude': Applied to parent BEFORE merge, then removed (not propagated)
    - 'hooks', 'tools', 'providers': Merge module lists by module ID
    - Dict values: Recursive deep merge
    - Other values: Child overrides parent

    Args:
        parent: Parent profile dictionary (loaded from parent profile)
        child: Child profile dictionary (loaded from child profile)

    Returns:
        Merged profile dictionary with child values taking precedence

    Example:
        >>> parent = {
        ...     "hooks": [{"module": "hooks-A", "source": "git+...", "config": {"a": 1}}],
        ...     "session": {"orchestrator": {"module": "X", "source": "git+..."}},
        ... }
        >>> child = {
        ...     "hooks": [{"module": "hooks-A", "config": {"b": 2}}],
        ...     "session": {"context": {"module": "Y"}},
        ... }
        >>> result = merge_profile_dicts(parent, child)
        >>> result["hooks"][0]["source"]  # Inherited from parent
        'git+...'
        >>> result["hooks"][0]["config"]  # Merged
        {'a': 1, 'b': 2}
        >>> result["session"]["orchestrator"]["module"]  # Inherited
        'X'
        >>> result["session"]["context"]["module"]  # Added
        'Y'

    Example with exclusions:
        >>> parent = {
        ...     "tools": [{"module": "tool-bash"}, {"module": "tool-web"}],
        ...     "hooks": [{"module": "hooks-logging"}],
        ... }
        >>> child = {
        ...     "exclude": {"tools": "all", "hooks": ["hooks-logging"]},
        ... }
        >>> result = merge_profile_dicts(parent, child)
        >>> result["tools"]  # Entire section excluded
        []
        >>> result["hooks"]  # Specific hook excluded
        []
        >>> "exclude" in result  # Exclusions not propagated
        False
    """
    # Extract exclusions from child (applied to parent, not propagated to result)
    child_copy = child.copy()
    exclusions = child_copy.pop("exclude", None)

    # Apply exclusions to parent before merging
    merged = parent.copy()
    if exclusions:
        merged = apply_exclusions(merged, exclusions)

    # Now merge child into (possibly excluded) parent
    for key, child_value in child_copy.items():
        if key not in merged:
            # New key in child - just add it
            merged[key] = child_value
        elif key in ("hooks", "tools", "providers"):
            # Module lists - merge by module ID
            merged[key] = merge_module_lists(merged[key], child_value)
        elif isinstance(child_value, dict) and isinstance(merged[key], dict):
            # Both are dicts - recursive deep merge
            merged[key] = merge_dicts(merged[key], child_value)
        else:
            # Scalar or type mismatch - child overrides parent
            merged[key] = child_value

    return merged


def merge_module_lists(parent_list: list[dict[str, Any]], child_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Merge module lists by module ID, deep-merging configs.

    Module lists (hooks, tools, providers) are matched by 'module' field.
    When the same module appears in both lists, their configs are deep-merged.

    Args:
        parent_list: Parent module list
        child_list: Child module list

    Returns:
        Merged module list with deep-merged configs

    Example:
        >>> parent = [{"module": "A", "source": "git+...", "config": {"x": 1}}]
        >>> child = [{"module": "A", "config": {"y": 2}}]
        >>> result = merge_module_lists(parent, child)
        >>> result[0]["source"]  # Inherited
        'git+...'
        >>> result[0]["config"]  # Merged
        {'x': 1, 'y': 2}
    """
    # Build dict indexed by module ID for efficient lookup
    result: dict[str, dict[str, Any]] = {}

    # Add all parent modules
    for item in parent_list:
        module_id = item.get("module")
        if module_id:
            result[module_id] = item.copy()

    # Merge or add child modules
    for child_item in child_list:
        module_id = child_item.get("module")
        if not module_id:
            # No module ID - can't merge, just append
            continue

        if module_id in result:
            # Same module in parent - deep merge
            result[module_id] = merge_module_items(result[module_id], child_item)
        else:
            # New module in child - add it
            result[module_id] = child_item.copy()

    # Return as list (order preserved from parent, then new child modules)
    return list(result.values())


def merge_module_items(parent_item: dict[str, Any], child_item: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge a single module item (hook/tool/provider config).

    Special handling for 'config' field - deep merged rather than replaced.
    All other fields follow standard merge rules (child overrides parent).

    Args:
        parent_item: Parent module item
        child_item: Child module item

    Returns:
        Merged module item

    Example:
        >>> parent = {"module": "A", "source": "git+...", "config": {"x": 1}}
        >>> child = {"module": "A", "config": {"y": 2}}
        >>> result = merge_module_items(parent, child)
        >>> result
        {'module': 'A', 'source': 'git+...', 'config': {'x': 1, 'y': 2}}
    """
    merged = parent_item.copy()

    for key, value in child_item.items():
        if key == "config" and key in merged:
            # Deep merge configs
            if isinstance(merged["config"], dict) and isinstance(value, dict):
                merged["config"] = merge_dicts(merged["config"], value)
            else:
                # Type mismatch or not dicts - child overrides
                merged["config"] = value
        else:
            # All other fields: child overrides parent (including 'source')
            merged[key] = value

    return merged


def merge_dicts(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """
    Recursive deep merge of two dictionaries.

    Child values override parent values at all nesting levels.
    If both parent and child have dict values for same key, merge recursively.

    Args:
        parent: Parent dictionary
        child: Child dictionary

    Returns:
        Merged dictionary

    Example:
        >>> parent = {"a": 1, "b": {"x": 1, "y": 2}}
        >>> child = {"b": {"x": 10, "z": 3}, "c": 4}
        >>> result = merge_dicts(parent, child)
        >>> result
        {'a': 1, 'b': {'x': 10, 'y': 2, 'z': 3}, 'c': 4}
    """
    merged = parent.copy()

    for key, value in child.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Both are dicts - recurse
            merged[key] = merge_dicts(merged[key], value)
        else:
            # Scalar, list, or type mismatch - child overrides
            merged[key] = value

    return merged
