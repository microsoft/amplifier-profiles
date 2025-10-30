"""Profile compiler that converts profiles to Mount Plans."""

import logging
from typing import TYPE_CHECKING
from typing import Any

from .schema import Profile

if TYPE_CHECKING:
    from .agent_loader import AgentLoader

logger = logging.getLogger(__name__)


def compile_profile_to_mount_plan(
    base: Profile,
    overlays: list[Profile] | None = None,
    agent_loader: "AgentLoader | None" = None,
) -> dict[str, Any]:
    """
    Compile a profile and its overlays into a Mount Plan.

    This function takes a base profile and optional overlay profiles and merges them
    into a single Mount Plan dictionary that can be passed to AmplifierSession.

    Per KERNEL_PHILOSOPHY:
    - Apps inject agent_loader (policy: where to search for agents)
    - Library provides mechanism (how to load agents from profile.agents config)

    Merge strategy:
    1. Start with base profile
    2. Apply each overlay in order (increasing precedence)
    3. Module lists are merged by module ID (later definitions override earlier ones)
    4. Session config fields are overridden (not merged)
    5. Load agents (if profile.agents config AND agent_loader provided)

    Args:
        base: Base profile to compile
        overlays: Optional list of overlay profiles to merge (in precedence order)
        agent_loader: Optional agent loader (app injects search paths via this)
                     If None, agents won't be loaded (profile.agents config ignored)

    Returns:
        Mount Plan dictionary suitable for AmplifierSession
    """
    if overlays is None:
        overlays = []

    # Extract from ModuleConfig objects directly
    orchestrator = base.session.orchestrator
    orchestrator_id = orchestrator.module
    orchestrator_source = orchestrator.source
    orchestrator_config = orchestrator.config or {}

    context = base.session.context
    context_id = context.module
    context_source = context.source
    context_config = context.config or {}

    # Start with base profile
    mount_plan: dict[str, Any] = {
        "session": {
            "orchestrator": orchestrator_id,
            "context": context_id,
        },
        "providers": [],
        "tools": [],
        "hooks": [],
        "agents": {},
    }

    # Add sources if present
    if orchestrator_source:
        mount_plan["session"]["orchestrator_source"] = orchestrator_source
    if context_source:
        mount_plan["session"]["context_source"] = context_source

    # Add config sections if present
    if orchestrator_config:
        mount_plan["orchestrator"] = {"config": orchestrator_config}
    if context_config:
        mount_plan["context"] = {"config": context_config}

    # Add base modules
    mount_plan["providers"] = [p.to_dict() for p in base.providers]
    mount_plan["tools"] = [t.to_dict() for t in base.tools]
    mount_plan["hooks"] = [h.to_dict() for h in base.hooks]

    # Apply overlays
    for overlay in overlays:
        mount_plan = _merge_profile_into_mount_plan(mount_plan, overlay)

    # Load agents using agent loading system (if agent_loader provided by app)
    # Per KERNEL_PHILOSOPHY: App injects policy (where to search) via agent_loader
    if base.agents and agent_loader is not None:
        agents_dict = {}

        # Determine which agents to load
        if base.agents.include:
            agent_names_to_load = base.agents.include
        elif base.agents.dirs:
            agent_names_to_load = agent_loader.list_agents()
        else:
            agent_names_to_load = []

        # Load agents from app-configured search locations
        for agent_name in agent_names_to_load:
            try:
                agent = agent_loader.load_agent(agent_name)
                agents_dict[agent_name] = agent.to_mount_plan_fragment()
                logger.debug(f"Loaded agent: {agent_name}")
            except Exception as e:
                # Log warning but continue loading other agents
                logger.warning(f"Failed to load agent '{agent_name}': {e}")

        mount_plan["agents"] = agents_dict
        logger.info(f"Loaded {len(agents_dict)} agents into mount plan")

    return mount_plan


def _merge_profile_into_mount_plan(mount_plan: dict[str, Any], overlay: Profile) -> dict[str, Any]:
    """
    Merge an overlay profile into an existing mount plan.

    Args:
        mount_plan: Existing mount plan to merge into
        overlay: Overlay profile to merge

    Returns:
        Updated mount plan
    """
    # Override session fields if present in overlay
    if overlay.session.orchestrator:
        mount_plan["session"]["orchestrator"] = overlay.session.orchestrator.module
        if overlay.session.orchestrator.source:
            mount_plan["session"]["orchestrator_source"] = overlay.session.orchestrator.source
        else:
            mount_plan["session"].pop("orchestrator_source", None)
        if overlay.session.orchestrator.config:
            if "orchestrator" not in mount_plan:
                mount_plan["orchestrator"] = {}
            mount_plan["orchestrator"]["config"] = overlay.session.orchestrator.config

    if overlay.session.context:
        mount_plan["session"]["context"] = overlay.session.context.module
        if overlay.session.context.source:
            mount_plan["session"]["context_source"] = overlay.session.context.source
        else:
            mount_plan["session"].pop("context_source", None)
        if overlay.session.context.config:
            if "context" not in mount_plan:
                mount_plan["context"] = {}
            mount_plan["context"]["config"] = overlay.session.context.config

    # Merge module lists
    mount_plan["providers"] = _merge_module_list(mount_plan["providers"], overlay.providers)
    mount_plan["tools"] = _merge_module_list(mount_plan["tools"], overlay.tools)
    mount_plan["hooks"] = _merge_module_list(mount_plan["hooks"], overlay.hooks)

    return mount_plan


def _merge_module_list(base_modules: list[dict[str, Any]], overlay_modules: list) -> list[dict[str, Any]]:
    """
    Merge two module lists, with overlay modules overriding base modules.

    Args:
        base_modules: Existing module list (already in dict format)
        overlay_modules: Overlay module list (ModuleConfig objects)

    Returns:
        Merged module list
    """
    # Convert overlay modules to dict format
    overlay_dicts = [m.to_dict() for m in overlay_modules]

    # Create dicts by ID for easy lookup
    base_by_id = {m["module"]: m for m in base_modules}
    overlay_by_id = {m["module"]: m for m in overlay_dicts}

    # Merge: start with base modules, override with overlay modules
    merged = base_by_id.copy()
    merged.update(overlay_by_id)

    # Return as list, preserving order
    result = []

    # Add base modules (potentially overridden)
    for base_module in base_modules:
        module_id = base_module["module"]
        result.append(merged[module_id])

    # Add new overlay modules (not in base)
    for overlay_module in overlay_dicts:
        module_id = overlay_module["module"]
        if module_id not in base_by_id:
            result.append(overlay_module)

    return result
