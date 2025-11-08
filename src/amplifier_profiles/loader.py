"""Profile loader for discovering and loading profile files."""

from pathlib import Path
from typing import Any

from amplifier_collections import extract_collection_name_from_path

from .exceptions import ProfileError
from .exceptions import ProfileNotFoundError
from .protocols import CollectionResolverProtocol
from .protocols import MentionLoaderProtocol
from .schema import Profile
from .utils import parse_frontmatter
from .utils import parse_markdown_body


class ProfileLoader:
    """Discovers and loads Amplifier profiles from multiple search paths."""

    def __init__(
        self,
        search_paths: list[Path],
        collection_resolver: CollectionResolverProtocol | None = None,
        mention_loader: MentionLoaderProtocol | None = None,
    ):
        """
        Initialize profile loader.

        Args:
            search_paths: List of paths to search for profiles
            collection_resolver: Optional collection resolver for collection:profile syntax
            mention_loader: Optional mention loader for @mention processing
        """
        self.search_paths = search_paths
        self.collection_resolver = collection_resolver
        self.mention_loader = mention_loader

    def list_profiles(self) -> list[str]:
        """
        Discover all available profile names.

        Returns profile names with collection prefix when from collections:
        - Simple: "base", "dev"
        - Collection: "design-intelligence:designer", "foundation:base"

        Returns:
            List of profile names
        """
        profiles = set()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            for profile_file in search_path.glob("*.md"):
                profile_name = profile_file.stem

                # Skip README files
                if profile_name.upper() == "README":
                    continue

                # Check if this profile is from a collection
                # Per DRY: Use library utility instead of manual parsing
                if "/collections/" in str(search_path):
                    collection_name = extract_collection_name_from_path(search_path)
                    if collection_name:
                        profiles.add(f"{collection_name}:{profile_name}")
                    else:
                        # Fallback if extraction fails
                        profiles.add(profile_name)
                else:
                    profiles.add(profile_name)

        return sorted(profiles)

    def find_profile_file(self, name: str) -> Path | None:
        """
        Find a profile file by name, checking paths in reverse order (highest precedence first).

        Supports multiple formats:
        1. Collection with simple name: "foundation:base" → searches collection/profiles/base.md
        2. Collection with full path: "foundation:profiles/base.md" → uses exact path
        3. Simple name: "base" → searches local paths

        Args:
            name: Profile name (simple or collection:path format)

        Returns:
            Path to profile file if found, None otherwise
        """
        # Collection syntax (foundation:base or foundation:profiles/base.md)
        if ":" in name:
            if not self.collection_resolver:
                return None

            collection_name, profile_path = name.split(":", 1)
            collection_path = self.collection_resolver.resolve(collection_name)
            if collection_path:
                # Try as full path first
                full_path = collection_path / profile_path
                if full_path.exists() and full_path.is_file():
                    return full_path

                # Try as simple name (foundation:base → profiles/base.md)
                if not profile_path.startswith("profiles/"):
                    simple_name = profile_path if profile_path.endswith(".md") else f"{profile_path}.md"
                    full_path = collection_path / "profiles" / simple_name
                    if full_path.exists() and full_path.is_file():
                        return full_path

                    # Hybrid packaging fallback: Check parent directory
                    # Per WORK_WITH_STANDARDS: Resources may be at parent level
                    if (collection_path / "pyproject.toml").exists():
                        parent_path = collection_path.parent / "profiles" / simple_name
                        if parent_path.exists() and parent_path.is_file():
                            return parent_path

            return None

        # Simple name: "base" (searches local paths)
        # Search in reverse order (highest precedence first)
        for search_path in reversed(self.search_paths):
            profile_file = search_path / f"{name}.md"
            if profile_file.exists():
                return profile_file

        return None

    def load_profile(self, name: str, _visited: set | None = None) -> Profile:
        """
        Load a profile with inheritance resolution.

        Args:
            name: Profile name (without .md extension)
            _visited: Set of already visited profiles (for circular detection)

        Returns:
            Fully resolved profile

        Raises:
            ProfileNotFoundError: If profile not found
            ProfileError: If circular inheritance or invalid profile
        """
        if _visited is None:
            _visited = set()

        if name in _visited:
            raise ProfileError(f"Circular dependency detected: {' -> '.join(_visited)} -> {name}")

        _visited.add(name)

        profile_file = self.find_profile_file(name)
        if profile_file is None:
            raise ProfileNotFoundError(f"Profile '{name}' not found in search paths")

        try:
            # Read file content (parse functions expect str, not Path)
            content = profile_file.read_text()
            data, _ = parse_frontmatter(content)  # Unpack tuple: (frontmatter_dict, body)
            markdown_body = parse_markdown_body(content)

            # NOTE: @mention processing happens in app layer (_process_profile_mentions)
            # Profile schema has no 'system' field, so any processing here would be lost.
            # This keeps ProfileLoader focused on YAML/module config loading only.

            # Store raw markdown in data for app layer to process
            # (Profile schema will drop this, but it's needed for documentation)
            if markdown_body:
                if "system" not in data:
                    data["system"] = {}
                if "instruction" not in data.get("system", {}):
                    data["system"]["instruction"] = markdown_body

            # Check for inheritance BEFORE validation
            extends = data.get("profile", {}).get("extends")

            if extends:
                # Load parent first
                parent = self.load_profile(extends, _visited)

                # Merge parent into child
                child_dict = data
                parent_dict = parent.model_dump()
                merged_data = self._deep_merge_dicts(parent_dict, child_dict)

                # Now validate the merged profile
                profile = Profile(**merged_data)
            else:
                # No inheritance, validate directly
                profile = Profile(**data)

            # Validate model pair if present
            if hasattr(profile.profile, "model") and profile.profile.model:
                self.validate_model_pair(profile.profile.model)

            return profile

        except Exception as e:
            raise ProfileError(f"Invalid profile file {profile_file}: {e}") from e

    def get_inheritance_chain(self, name: str) -> list[str]:
        """
        Get the inheritance chain for a profile.

        Returns profile names from root to current (e.g., ['foundation:foundation', 'foundation:base', 'developer-expertise:dev']).

        Args:
            name: Profile name (simple or collection:profile format)

        Returns:
            List of profile names from root parent to current profile

        Raises:
            ProfileNotFoundError: If profile not found
            ProfileError: If circular inheritance detected
        """
        chain = []
        current_name = name
        visited = set()

        while current_name:
            if current_name in visited:
                raise ProfileError(f"Circular dependency detected: {' → '.join(chain)} → {current_name}")

            visited.add(current_name)
            chain.append(current_name)

            profile_file = self.find_profile_file(current_name)
            if not profile_file:
                raise ProfileNotFoundError(f"Profile '{current_name}' not found in search paths")

            try:
                content = profile_file.read_text()
                data, _ = parse_frontmatter(content)
                current_name = data.get("profile", {}).get("extends")
            except Exception as e:
                raise ProfileError(f"Failed to read profile {profile_file}: {e}") from e

        return list(
            reversed(chain)
        )  # Root first: ['foundation:foundation', 'foundation:base', 'developer-expertise:dev']

    def load_inheritance_chain_profiles(self, name: str) -> list[Profile]:
        """
        Load and merge the complete inheritance chain, validating only the final result.

        This allows child profiles to be partial - they only need to specify what differs
        from parent profiles. Validation happens after merging the complete chain.

        Args:
            name: Profile name (simple or collection:profile format)

        Returns:
            List containing single merged Profile object

        Raises:
            ProfileNotFoundError: If profile not found
            ProfileError: If circular inheritance or invalid merged profile
        """
        from pydantic import ValidationError

        from amplifier_profiles.merger import merge_profile_dicts

        chain_names = self.get_inheritance_chain(name)
        profile_dicts = []
        profile_files = []

        # Step 1: Load all profiles as dictionaries (no validation yet)
        for profile_name in chain_names:
            profile_file = self.find_profile_file(profile_name)
            if not profile_file:
                raise ProfileNotFoundError(f"Profile '{profile_name}' not found")

            profile_files.append(profile_file)

            try:
                content = profile_file.read_text()
                data, _ = parse_frontmatter(content)
                markdown_body = parse_markdown_body(content)

                # NOTE: @mention processing happens in app layer (_process_profile_mentions)
                # Profile schema has no 'system' field, so processing here would be dropped.
                # Store raw markdown for documentation/display purposes only.
                if markdown_body:
                    if "system" not in data:
                        data["system"] = {}
                    if "instruction" not in data.get("system", {}):
                        data["system"]["instruction"] = markdown_body

                profile_dicts.append(data)

            except Exception as e:
                raise ProfileError(f"Failed to load profile file {profile_file}: {e}") from e

        # Step 2: Merge all profiles from parent to child
        merged = {}
        for profile_dict in profile_dicts:
            merged = merge_profile_dicts(merged, profile_dict)

        # Step 3: Validate merged result
        try:
            final_profile = Profile(**merged)
        except ValidationError as e:
            # Enhanced error message with full context
            error_msg = self._format_validation_error(e, chain_names, profile_files)
            raise ProfileError(error_msg) from e

        return [final_profile]

    def load_inheritance_chain_dicts(self, name: str) -> list[dict[str, Any]]:
        """
        Load inheritance chain as raw dictionaries for provenance tracking.

        This method loads each profile in the chain as a dictionary without validation
        or merging. It's useful for display purposes where you want to show which
        profile contributed which values.

        Args:
            name: Profile name (simple or collection:profile format)

        Returns:
            List of profile dictionaries from root to leaf (unvalidated, unmerged)

        Raises:
            ProfileNotFoundError: If profile not found
            ProfileError: If profile file cannot be loaded

        Example:
            >>> loader = ProfileLoader(...)
            >>> dicts = loader.load_inheritance_chain_dicts("dev")
            >>> # dicts[0] = foundation (raw dict)
            >>> # dicts[1] = base (raw dict)
            >>> # dicts[2] = dev (raw dict)
        """
        chain_names = self.get_inheritance_chain(name)
        profile_dicts = []

        for profile_name in chain_names:
            profile_file = self.find_profile_file(profile_name)
            if not profile_file:
                raise ProfileNotFoundError(f"Profile '{profile_name}' not found")

            try:
                content = profile_file.read_text()
                data, _ = parse_frontmatter(content)
                markdown_body = parse_markdown_body(content)

                # Add profile name to dict for display purposes
                if "profile" in data and "name" not in data["profile"]:
                    data["profile"]["name"] = profile_name

                # Store markdown for display
                if markdown_body:
                    if "system" not in data:
                        data["system"] = {}
                    if "instruction" not in data.get("system", {}):
                        data["system"]["instruction"] = markdown_body

                profile_dicts.append(data)

            except Exception as e:
                raise ProfileError(f"Failed to load profile file {profile_file}: {e}") from e

        return profile_dicts

    def _format_validation_error(self, error: Any, chain_names: list[str], profile_files: list[Path]) -> str:
        """
        Format Pydantic validation errors with helpful context.

        Args:
            error: Pydantic validation error
            chain_names: Profile inheritance chain names
            profile_files: Profile file paths

        Returns:
            Formatted error message with suggestions
        """
        errors = []
        for err in error.errors():
            loc = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            type_ = err["type"]

            if type_ == "missing":
                errors.append(f"  • Missing required field: {loc}")
            elif type_ == "type_error":
                errors.append(f"  • Wrong type for {loc}: {msg}")
            else:
                errors.append(f"  • {loc}: {msg}")

        chain_display = " → ".join(chain_names)
        error_list = "\n".join(errors)

        return (
            f"Merged profile is incomplete after inheritance\n\n"
            f"Inheritance chain: {chain_display}\n\n"
            f"Validation errors:\n{error_list}\n\n"
            f"This usually means:\n"
            f"  - Base profile doesn't define all required fields\n"
            f"  - Or fields were accidentally removed during inheritance\n\n"
            f"Suggestions:\n"
            f"  1. Check base profiles have complete session/providers configuration\n"
            f"  2. Verify module sources are defined in root or parent profiles\n"
            f"  3. See docs/PROFILE_AUTHORING.md for examples\n\n"
            f"Profile location: {profile_files[-1]}"
        )

    def get_profile_source(self, name: str) -> str | None:
        """
        Determine which source a profile comes from.

        Args:
            name: Profile name (simple or collection:profile format)

        Returns:
            "bundled", "bundled-collection", "project", "project-collection",
            "user", "user-collection", or None if not found
        """
        profile_file = self.find_profile_file(name)
        if profile_file is None:
            return None

        path_str = str(profile_file)

        # Check for collections first
        if "/collections/" in path_str:
            if "amplifier_app_cli" in path_str and "data/collections" in path_str:
                return "bundled"
            if ".amplifier/collections" in path_str and str(Path.home()) not in path_str:
                return "project-collection"
            if str(Path.home()) in path_str and ".amplifier/collections" in path_str:
                return "user-collection"
            return "collection"

        # Non-collection profiles
        if str(Path.home()) in path_str and ".amplifier/profiles" in path_str:
            return "user"
        if ".amplifier/profiles" in path_str:
            return "project"
        if "amplifier_app_cli" in path_str:
            return "bundled"

        return "unknown"

    def validate_model_pair(self, model: str) -> None:
        """
        Validate model is in 'provider/model' format.

        Args:
            model: Model string to validate

        Raises:
            ProfileError: If format is invalid
        """
        if "/" not in model:
            raise ProfileError(f"Model must be 'provider/model' format, got: {model}")

        provider, model_name = model.split("/", 1)
        if not provider or not model_name:
            raise ProfileError(f"Invalid model pair: {model}")

    def _merge_module_lists(self, parent_list: list, child_list: list) -> list:
        """
        Merge module lists (tools, providers, hooks) by module ID.

        Strategy:
        - Start with all parent modules
        - Child modules with same ID override parent
        - Child modules with new ID are appended

        Result: Child inherits parent modules + can override specific ones + add new ones

        Args:
            parent_list: Parent module list
            child_list: Child module list

        Returns:
            Merged module list
        """
        # Build dict keyed by module ID for deduplication
        result_dict: dict[str, dict] = {}

        # Add all parent modules
        for item in parent_list:
            if isinstance(item, dict) and "module" in item:
                result_dict[item["module"]] = item

        # Override/append child modules
        for item in child_list:
            if isinstance(item, dict) and "module" in item:
                result_dict[item["module"]] = item  # Override parent or add new

        return list(result_dict.values())

    def _deep_merge_dicts(self, parent: dict, child: dict) -> dict:
        """
        Recursively merge dictionaries with proper module list handling.

        Args:
            parent: Parent dictionary
            child: Child dictionary

        Returns:
            Merged dictionary
        """
        result = parent.copy()

        for key, value in child.items():
            if value is None:
                # Explicit None removes inherited value
                result.pop(key, None)
            elif isinstance(value, dict) and key in result and isinstance(result[key], dict):
                # Deep merge nested dicts
                result[key] = self._deep_merge_dicts(result[key], value)
            elif isinstance(value, list) and key in result and isinstance(result[key], list):
                # Module lists get merged by module ID
                if key in ("tools", "providers", "hooks"):
                    result[key] = self._merge_module_lists(result[key], value)
                else:
                    # Other lists get replaced
                    result[key] = value
            else:
                # Replace value
                result[key] = value

        return result
