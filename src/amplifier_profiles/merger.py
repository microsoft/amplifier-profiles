"""Profile merging utilities for inheritance.

This module implements deep merging of profile configurations, allowing child
profiles to be partial and inherit from parent profiles without duplication.

Key principles:
- Module lists (hooks/tools/providers) are merged by module ID
- Config dictionaries are recursively deep-merged
- Sources are inherited - child profiles don't need to repeat git URLs
- Scalars override - simple values in child replace parent values

This supports the "merge-then-validate" pattern where validation happens
after the complete inheritance chain is merged.
"""

from typing import Any


def merge_profile_dicts(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge child profile dictionary into parent profile dictionary.

    Merge rules by key:
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
    """
    merged = parent.copy()

    for key, child_value in child.items():
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
