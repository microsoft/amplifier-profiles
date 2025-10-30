# amplifier-profiles

**Profile and agent loading, inheritance, and Mount Plan compilation for Amplifier applications**

amplifier-profiles provides complete profile and agent lifecycle management: discovery from search paths, loading with frontmatter parsing, inheritance resolution with cycle detection, deep merging across overlays, @mention expansion, and compilation to Mount Plans ready for AmplifierSession.

---

## Installation

```bash
# From PyPI (when published)
uv pip install amplifier-profiles

# From git (development)
uv pip install git+https://github.com/microsoft/amplifier-profiles@main

# For local development
cd amplifier-profiles
uv pip install -e .

# Or using uv sync for development with dependencies
uv sync --dev
```

---

## Quick Start

```python
from amplifier_profiles import ProfileLoader, compile_profile_to_mount_plan
from amplifier_core import AmplifierSession
from pathlib import Path

# Define search paths for your application
search_paths = [
    Path(__file__).parent / "data" / "profiles",  # Bundled
    Path.home() / ".amplifier" / "profiles",      # User
    Path(".amplifier/profiles"),                   # Project
]

# Create loader
loader = ProfileLoader(search_paths=search_paths)

# Load simple profile
profile = loader.load_profile("dev")

# Or load profile from collection (collection:name syntax)
profile = loader.load_profile("developer-expertise:dev")

# Or load with full path within collection
profile = loader.load_profile("design-intelligence:profiles/designer.md")

# Compile to Mount Plan
mount_plan = compile_profile_to_mount_plan(profile)

# Use with AmplifierSession
async with AmplifierSession(config=mount_plan) as session:
    response = await session.execute("Hello, Amplifier!")
    print(response)
```

---

## What This Library Provides

### Profile Management

**Profiles** are reusable configuration bundles defined in Markdown files with YAML frontmatter:

```markdown
---
profile:
  name: my-profile
  version: 1.0.0
  description: My specialized profile
  extends: base  # Inheritance support

session:
  orchestrator: loop-streaming
  context: context-persistent

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      model: claude-sonnet-4-5
      temperature: 0.7

tools:
  - module: tool-filesystem
  - module: tool-bash

hooks:
  - module: hooks-logging

agents:
  dirs: ["./agents"]
  include: ["zen-architect", "bug-hunter"]
---

Optional context or system instruction in markdown body.
```

**Key features**:
- Multi-level inheritance via `extends` field
- Overlay merging (multiple profiles with same name)
- Collection syntax support (`foundation:base`)
- @mention expansion in markdown body
- Compilation to Mount Plan for AmplifierSession

### Agent Management

**Agents** are specialized sub-session configurations (partial mount plans):

```markdown
---
meta:
  name: my-agent
  description: Specialized expert agent

providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      model: claude-opus-4-1
      temperature: 0.7

tools:
  - module: tool-filesystem
  - module: tool-bash

session:
  max_tokens: 100000
---

You are a specialized expert in [domain].

[Detailed agent instructions]

Can reference @collection:context/expertise.md for shared knowledge.
```

**Key features**:
- No inheritance (simpler than profiles)
- System instruction in markdown body
- @mention expansion support
- First-match-wins resolution (no overlay merging)

### Inheritance Resolution

Profiles support multi-level inheritance:

```yaml
# foundation.md (base)
profile:
  name: foundation
providers:
  - module: provider-anthropic
    config: {model: claude-sonnet-4-5}

# base.md (extends foundation)
profile:
  name: base
  extends: foundation
tools:
  - module: tool-filesystem

# dev.md (extends base, which extends foundation)
profile:
  name: dev
  extends: base
hooks:
  - module: hooks-logging
```

**Resolution process**:
1. Load child profile (dev)
2. Detect extends field → load parent (base)
3. Detect parent's extends field → load grandparent (foundation)
4. Build inheritance chain: [foundation, base, dev]
5. Merge foundation → base → dev
6. Detect cycles (raise error if found)

**Result**: dev profile has providers from foundation, tools from base, hooks from dev.

### Overlay Merging

Multiple profiles with same name across search paths become overlays:

```
~/.amplifier/profiles/dev.md          # Lowest precedence
.amplifier/profiles/dev.md            # Higher (project override)
```

**Resolution process**:
1. Find all files named "dev.md" across search paths
2. Load each profile
3. Merge in precedence order (lowest to highest)

**Use case**: Project customizes user-global profile without duplicating entire configuration.

---

## API Reference

### Schemas

#### Profile Models

```python
from amplifier_profiles import (
    Profile, ProfileMetadata, SessionConfig, ModuleConfig,
    AgentsConfig
)

class ProfileMetadata(BaseModel):
    """Profile identification and inheritance."""
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    description: str
    model: str | None = None
    extends: str | None = None  # Parent profile name

class ModuleConfig(BaseModel):
    """Module specification with source and config."""
    model_config = ConfigDict(frozen=True)

    module: str
    source: str | dict[str, Any] | None = None
    config: dict[str, Any] | None = None

class SessionConfig(BaseModel):
    """Session-level module configuration."""
    model_config = ConfigDict(frozen=True)

    orchestrator: ModuleConfig
    context: ModuleConfig

class Profile(BaseModel):
    """Complete profile specification."""
    model_config = ConfigDict(frozen=True)

    profile: ProfileMetadata
    session: SessionConfig
    providers: list[ModuleConfig] = Field(default_factory=list)
    tools: list[ModuleConfig] = Field(default_factory=list)
    hooks: list[ModuleConfig] = Field(default_factory=list)
    agents: AgentsConfig | None = None
```

#### Agent Models

```python
from amplifier_profiles import Agent, AgentMetadata

class AgentMetadata(BaseModel):
    """Agent identification."""
    model_config = ConfigDict(frozen=True)

    name: str
    description: str

class Agent(BaseModel):
    """Agent specification (partial mount plan)."""
    model_config = ConfigDict(frozen=True)

    meta: AgentMetadata
    providers: list[ModuleConfig] = Field(default_factory=list)
    tools: list[ModuleConfig] = Field(default_factory=list)
    hooks: list[ModuleConfig] = Field(default_factory=list)
    session: dict[str, Any] | None = None
    system: dict[str, str] | None = None  # {"instruction": str}

    def to_mount_plan_fragment(self) -> dict[str, Any]:
        """Convert to partial mount plan for agent delegation."""
```

### Profile Loading

```python
from amplifier_profiles import ProfileLoader
from pathlib import Path

class ProfileLoader:
    """Discover and load profiles from search paths."""

    def __init__(
        self,
        search_paths: list[Path],
        collection_resolver: CollectionResolverProtocol | None = None,
        mention_loader: MentionLoaderProtocol | None = None
    ):
        """Initialize with app-specific configuration.

        Args:
            search_paths: Paths to search (lowest to highest precedence)
            collection_resolver: Optional for "collection:profile" syntax
            mention_loader: Optional for @mention expansion
        """

# Create loader (minimal - no optional dependencies)
loader = ProfileLoader(search_paths=[Path("profiles")])

# Create loader (full - with optional dependencies)
from amplifier_collections import CollectionResolver
from amplifier_app_cli.lib.mention_loading import MentionLoader

loader = ProfileLoader(
    search_paths=[...],
    collection_resolver=CollectionResolver(search_paths=[...]),
    mention_loader=MentionLoader(...),
)
```

#### Methods

```python
# List all available profiles (includes collection profiles)
profiles = loader.list_profiles()
# Returns: ["base", "dev", "developer-expertise:dev", "design-intelligence:designer"]

# Find profile file by name (simple)
path = loader.find_profile_file("dev")

# Find profile file by collection syntax
path = loader.find_profile_file("developer-expertise:dev")

# Find profile file with full path
path = loader.find_profile_file("design-intelligence:profiles/designer.md")
# Returns: Path to profile file or None

# Load profile (with inheritance and overlays resolved)
profile = loader.load_profile("dev")  # Simple name
# Or: loader.load_profile("developer-expertise:dev")  # Collection syntax
# Or: loader.load_profile("design-intelligence:profiles/designer.md")  # Full path
# Returns: Profile model

# Resolve inheritance chain
chain = loader.resolve_inheritance(profile)
# Returns: [parent, child, grandchild] in merge order

# Load overlays for a name
overlays = loader.load_overlays("dev")
# Returns: List of profiles from different search paths

# Merge two profiles
merged = loader.merge_profiles(parent, child)
# Returns: New merged Profile

# Get profile source label
source = loader.get_profile_source("dev")
# Returns: "bundled" | "user" | "project" | "collection-name"
```

### Agent Loading

```python
from amplifier_profiles import AgentResolver, AgentLoader

class AgentResolver:
    """Resolve agent names to files."""

    def __init__(
        self,
        search_paths: list[Path],
        collection_resolver: CollectionResolverProtocol | None = None
    ):
        """Initialize with app-specific search paths."""

# Create resolver
resolver = AgentResolver(
    search_paths=[Path("agents")],
    collection_resolver=None  # Optional
)

# Resolve agent name to file (simple name)
path = resolver.resolve("zen-architect")

# Or resolve with collection syntax
path = resolver.resolve("developer-expertise:zen-architect")

# Or resolve with full path
path = resolver.resolve("design-intelligence:agents/art-director.md")
# Returns: Path | None

# List all agents (includes collection agents)
agents = resolver.list_agents()
# Returns: ["zen-architect", "bug-hunter", "developer-expertise:zen-architect", "design-intelligence:art-director"]

class AgentLoader:
    """Load and parse agent definitions."""

    def __init__(
        self,
        resolver: AgentResolver | None = None,
        mention_loader: MentionLoaderProtocol | None = None
    ):
        """Initialize with optional resolver and mention loader."""

# Create loader
loader = AgentLoader(resolver=resolver, mention_loader=None)

# Load agent (simple name)
agent = loader.load_agent("zen-architect")

# Or load from collection
agent = loader.load_agent("developer-expertise:zen-architect")

# Or load with full path
agent = loader.load_agent("design-intelligence:agents/art-director.md")
# Returns: Agent model

# Load multiple agents (can mix simple and collection syntax)
agents = loader.load_agents_by_names([
    "bug-hunter",  # Simple name
    "developer-expertise:zen-architect",  # Collection syntax
    "design-intelligence:art-director"  # Collection syntax
])
# Returns: {"bug-hunter": {...}, "developer-expertise:zen-architect": {...}, ...}

# Get agent source
source = loader.get_agent_source("zen-architect")
# Returns: "bundled" | "user" | "project" | "collection-name"
```

### Compilation

```python
from amplifier_profiles import compile_profile_to_mount_plan

def compile_profile_to_mount_plan(
    base: Profile,
    overlays: list[Profile] | None = None
) -> dict[str, Any]:
    """Compile profile(s) to Mount Plan for AmplifierSession.

    Process:
    1. Extract session config (orchestrator, context)
    2. Build module lists (providers, tools, hooks)
    3. Apply overlays (merge in precedence order)
    4. Load agents (if agents config present)
    5. Inject profile-level configs (task, ui, logging)

    Args:
        base: Base profile to compile
        overlays: Optional list of overlay profiles (precedence order)

    Returns:
        Mount Plan dictionary suitable for AmplifierSession

    Example:
        >>> profile = loader.load_profile("dev")
        >>> mount_plan = compile_profile_to_mount_plan(profile)
        >>> async with AmplifierSession(config=mount_plan) as session:
        ...     response = await session.execute("test")
    """
```

**Mount Plan structure**:

```python
{
    "session": {
        "orchestrator": "loop-streaming",
        "orchestrator_source": "git+https://...",
        "context": "context-persistent",
        "context_source": "git+https://...",
    },
    "providers": [
        {"module": "provider-anthropic", "source": "git+...", "config": {...}}
    ],
    "tools": [...],
    "hooks": [...],
    "agents": {
        "agent-name": {
            "description": "...",
            "providers": [...],
            "tools": [...],
            "system": {"instruction": "..."}
        }
    },
    "orchestrator": {"config": {...}},  # Optional profile-level config
    "context": {"config": {...}},       # Optional profile-level config
}
```

### Utilities

```python
from amplifier_profiles import parse_frontmatter, parse_markdown_body

# Parse frontmatter and body
frontmatter, body = parse_frontmatter(file_content)
# Returns: (dict, str)

# Extract just markdown body
body = parse_markdown_body(file_content)
# Returns: str (content after ---...--- block)
```

---

## Usage Examples

### CLI Application (Full Features)

```python
from amplifier_profiles import ProfileLoader, AgentLoader, compile_profile_to_mount_plan
from amplifier_collections import CollectionResolver
from amplifier_app_cli.lib.mention_loading import MentionLoader
from amplifier_core import AmplifierSession
from pathlib import Path

# Set up collection resolver
collection_resolver = CollectionResolver(search_paths=[
    Path(__file__).parent / "data" / "collections",
    Path.home() / ".amplifier" / "collections",
    Path(".amplifier/collections"),
])

# Set up mention loader
mention_loader = MentionLoader(...)

# Set up profile loader with all optional features
profile_loader = ProfileLoader(
    search_paths=[
        Path(__file__).parent / "data" / "profiles",
        Path.home() / ".amplifier" / "profiles",
        Path(".amplifier/profiles"),
    ],
    collection_resolver=collection_resolver,
    mention_loader=mention_loader,
)

# Load and compile profile
profile = profile_loader.load_profile("dev")
mount_plan = compile_profile_to_mount_plan(profile)

# Create session
async with AmplifierSession(config=mount_plan) as session:
    response = await session.execute("Analyze this code...")
    print(response)
```

### Web Application (Minimal Features)

```python
from amplifier_profiles import ProfileLoader, compile_profile_to_mount_plan
from amplifier_core import AmplifierSession
from pathlib import Path

class WebProfileService:
    """Profile service for web application."""

    def __init__(self, workspace_id: str):
        # Web-specific paths (no collections, no mentions)
        self.search_paths = [
            Path("/var/amplifier/system/profiles"),
            Path(f"/var/amplifier/workspaces/{workspace_id}/profiles"),
        ]

        # Simple loader (no optional dependencies)
        self.loader = ProfileLoader(
            search_paths=self.search_paths,
            collection_resolver=None,  # Web doesn't use collections
            mention_loader=None,        # Web doesn't support @mentions
        )

    async def execute_with_profile(self, profile_name: str, prompt: str):
        """Execute prompt with profile."""
        profile = self.loader.load_profile(profile_name)
        mount_plan = compile_profile_to_mount_plan(profile)

        # Web-specific customization (add workspace hook)
        mount_plan["hooks"].append({
            "module": "hooks-web-logger",
            "config": {"workspace_id": self.workspace_id}
        })

        async with AmplifierSession(config=mount_plan) as session:
            return await session.execute(prompt)
```

### Desktop Application (Platform-Specific Paths)

```python
from amplifier_profiles import ProfileLoader, compile_profile_to_mount_plan
from pathlib import Path
import platformdirs

class DesktopProfileManager:
    """Profile management for desktop application."""

    def __init__(self, app_name: str = "Amplifier"):
        # Platform-appropriate paths (macOS/Windows/Linux)
        app_data = platformdirs.user_data_dir(app_name)

        self.search_paths = [
            Path(__file__).parent / "resources" / "profiles",  # Bundled
            Path(app_data) / "profiles",                       # User
            Path.cwd() / ".amplifier" / "profiles",            # Project
        ]

        self.loader = ProfileLoader(search_paths=self.search_paths)

    def list_available_profiles(self) -> list[str]:
        """List profiles for UI dropdown."""
        return self.loader.list_profiles()

    async def run_with_profile(self, profile_name: str, prompt: str):
        """Run prompt with selected profile."""
        profile = self.loader.load_profile(profile_name)
        mount_plan = compile_profile_to_mount_plan(profile)

        async with AmplifierSession(config=mount_plan) as session:
            return await session.execute(prompt)
```

### Testing (Validation Tool)

```python
from amplifier_profiles import ProfileLoader, compile_profile_to_mount_plan
from pathlib import Path

class ProfileValidator:
    """Validate profile definitions for CI/CD."""

    def __init__(self, profiles_dir: Path):
        self.loader = ProfileLoader(
            search_paths=[profiles_dir],
            collection_resolver=None,
            mention_loader=None,
        )

    def validate_all(self) -> dict[str, bool | str]:
        """Validate all profiles compile successfully."""
        results = {}

        for profile_name in self.loader.list_profiles():
            try:
                profile = self.loader.load_profile(profile_name)
                mount_plan = compile_profile_to_mount_plan(profile)

                # Validate mount plan structure
                assert "session" in mount_plan, "Missing session config"
                assert "providers" in mount_plan, "Missing providers"
                assert mount_plan["session"]["orchestrator"], "Missing orchestrator"

                results[profile_name] = True
            except Exception as e:
                results[profile_name] = f"Error: {e}"

        return results

# Use in CI
validator = ProfileValidator(Path("profiles"))
results = validator.validate_all()

for name, status in results.items():
    if status is True:
        print(f"✓ {name}")
    else:
        print(f"✗ {name}: {status}")
```

---

## Collection Syntax

### Profile References

Profiles can extend profiles from collections:

```yaml
# dev.md extends base from foundation collection
profile:
  name: dev
  extends: foundation:base  # Collection syntax

# Also supports full path
profile:
  name: dev
  extends: foundation:profiles/base.md
```

### Context References

Profiles can reference context from collections via @mentions:

```yaml
context:
  - @foundation:context/shared/base.md
  - @user:notes/project-context.md
  - @project:docs/requirements.md
```

**Expansion**: If `mention_loader` provided, @mentions expand to file contents.

---

## @Mention Expansion

### In Profile Body

```markdown
---
profile:
  name: dev
---

You are an AI assistant for development.

@foundation:context/implementation-philosophy.md

@project:context/coding-standards.md
```

**Process**:
1. Parse markdown body from profile
2. Extract @mention patterns
3. Use mention_loader to load referenced files (if provided)
4. Insert file contents at mention locations

**Without mention_loader**: Body preserved as-is (no expansion).

### In Agent Instructions

```markdown
---
meta:
  name: architect
---

You are a system architect.

@foundation:context/architecture-principles.md

When designing systems, consider:
- [Architecture guidelines from loaded context]
```

**Same process**: Mention loader expands references if provided.

---

## Advanced Usage

### Custom Profile Merging

```python
from amplifier_profiles import ProfileLoader

loader = ProfileLoader(search_paths=[...])

# Load base and child separately
parent = loader.load_profile("base")
child = loader.load_profile("dev")

# Custom merge logic
merged = loader.merge_profiles(parent, child)

# Compile merged profile
mount_plan = compile_profile_to_mount_plan(merged)
```

### Inheritance Chain Inspection

```python
# Load profile
profile = loader.load_profile("dev")

# Inspect full inheritance chain
chain = loader.resolve_inheritance(profile)

print("Inheritance chain:")
for p in chain:
    print(f"  {p.profile.name} (v{p.profile.version})")

# Output:
# Inheritance chain:
#   foundation (v1.0.0)
#   base (v1.0.0)
#   dev (v2.0.0)
```

### Agent Discovery from Profile

```python
# Profile specifies agent discovery
profile = loader.load_profile("dev")

if profile.agents:
    agent_loader = AgentLoader(...)

    # Load agents specified in profile
    if profile.agents.include:
        agents = agent_loader.load_agents_by_names(profile.agents.include)
        # Returns: {"zen-architect": {...}, "bug-hunter": {...}}

    # Or discover from directories
    if profile.agents.dirs:
        # Scan specified directories for agents
        ...
```

### Mount Plan Customization

```python
# Load and compile profile
profile = loader.load_profile("base")
mount_plan = compile_profile_to_mount_plan(profile)

# App-specific customization before using
mount_plan["hooks"].append({
    "module": "hooks-app-specific",
    "config": {"app_id": "my-app"}
})

# Use customized plan
async with AmplifierSession(config=mount_plan) as session:
    ...
```

---

## Error Handling

### Exceptions

```python
from amplifier_profiles import ProfileError, AgentError

# Profile errors
try:
    profile = loader.load_profile("nonexistent")
except ProfileError as e:
    print(f"Error: {e.message}")
    print(f"Searched: {e.context.get('search_paths')}")

# Agent errors
try:
    agent = agent_loader.load_agent("unknown")
except AgentError as e:
    print(f"Error: {e.message}")
    print(f"Context: {e.context}")
```

### Validation Errors

```python
# Invalid profile format
try:
    profile = loader.load_profile("broken")
except ProfileError as e:
    # Pydantic validation errors included in context
    print(f"Validation failed: {e.context.get('errors')}")

# Circular inheritance
try:
    # a.md extends b, b.md extends a
    profile = loader.load_profile("a")
except ProfileError as e:
    print(f"Cycle detected: {e.context.get('chain')}")
```

---

## Design Philosophy

### Mechanism, Not Policy

The library provides profile **mechanism**:
- **How** to load profiles (file parsing, frontmatter extraction)
- **How** to resolve inheritance (chain building, cycle detection)
- **How** to merge (deep recursive merge)
- **How** to compile (Profile → Mount Plan transformation)

Applications provide profile **policy**:
- **Where** to search for profiles (path conventions)
- **What** profiles mean (interpretation and display)
- **When** to load (caching strategy)
- **Which** optional features to use (collections, mentions)

### Protocol-Based Integration

**Why optional dependencies?**

Not all applications need collections or @mentions:

```python
# Minimal (no optional features)
loader = ProfileLoader(
    search_paths=[Path("profiles")],
    collection_resolver=None,
    mention_loader=None,
)

# Full-featured (all optional features)
loader = ProfileLoader(
    search_paths=[...],
    collection_resolver=CollectionResolver(...),
    mention_loader=MentionLoader(...),
)
```

**Benefit**: Library works in constrained environments (web services, embedded systems) without requiring full feature set.

### Frozen Models Rationale

**Why immutable Pydantic models?**

```python
class Profile(BaseModel):
    model_config = ConfigDict(frozen=True)
```

**Benefits**:
- Thread-safe by default (no accidental mutations)
- Clear data flow (transformations create new instances)
- Easier to test (no hidden state changes)
- Simpler reasoning (no mutation tracking needed)

**Trade-off**: Slightly more verbose (create new instances to modify)

**Decision**: Safety and clarity worth the verbosity.

---

## Dependencies

### Runtime

**Required**:
- pyyaml >=6.0 (YAML parsing)
- pydantic >=2.0 (schema validation, frozen models)
- Python >=3.11 (stdlib: pathlib, typing)

**Optional** (via protocols):
- Collection resolver (for collection syntax support)
- Mention loader (for @mention expansion)

### Development

- pytest >=8.0
- pytest-cov (coverage)

**Philosophy**: Core dependencies (pyyaml, pydantic) with protocol-based integration for optional features (collections, mentions).

---

## Testing

### Running Tests

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Or using uv sync
uv sync --dev

# Run tests
pytest

# Run with coverage
pytest --cov=amplifier_profiles --cov-report=html
```

### Test Coverage

The library includes comprehensive tests:

- **Unit tests**: Frontmatter parsing, inheritance resolution, merge semantics
- **Integration tests**: Multi-level inheritance, overlay merging, collection syntax
- **Protocol tests**: Works without collection_resolver, works without mention_loader
- **Edge cases**: Circular inheritance, missing files, invalid YAML

Target coverage: >90%

---

## Design Decisions

### Why Separate Profile and Agent Models?

**Alternative**: Single unified model

**Problem**: Different semantics (inheritance, merging, compilation)

**Solution**: Separate models with shared primitives (ModuleConfig)

**Benefits**:
- Type safety (profiles have inheritance, agents don't)
- Clear separation of concerns
- Simpler validation

### Why First-Match-Wins for Agents?

**Alternative**: Overlay merging like profiles

**Problem**: Agents are simpler, merging adds complexity

**Solution**: First match from highest precedence path wins

**Rationale**:
- Agents don't have inheritance
- Merging agent instructions is ambiguous
- Simpler is better (YAGNI principle)

### Why Protocol-Based Optional Dependencies?

**Alternative**: Hard dependency on CollectionResolver and MentionLoader

**Problem**:
- Circular dependency risk
- Couples library to specific implementations
- Forces all apps to support all features

**Solution**: Accept any protocol implementation (or None)

**Benefits**:
- No circular dependencies (can't happen with protocols)
- Library works in minimal environments
- Apps choose which features to enable
- Testing easier (mock protocol implementations)

---

## Philosophy Compliance

### Kernel Philosophy ✅

**"Mechanism, not policy"**:
- ✅ Library: How to load/merge/compile profiles (mechanism)
- ✅ App: Where to search, how to display (policy)

**"Extensibility through composition"**:
- ✅ Optional features via protocol injection (not config flags)
- ✅ Search paths injectable (not hardcoded)

**"Text-first, inspectable surfaces"**:
- ✅ Markdown + YAML (human-readable)
- ✅ Pydantic schemas (self-documenting)
- ✅ Mount Plans (JSON-serializable dicts)

### Modular Design Philosophy ✅

**"Bricks & studs"**:
- **Studs**: ProfileLoader, AgentLoader, compile_profile_to_mount_plan APIs
- **Bricks**: Implementation of loading/merging/compilation logic
- **Regeneratable**: Can rewrite internals while preserving API contracts

### Ruthless Simplicity ✅

**No abstract base classes**: Protocols are sufficient

**No caching**: Load profiles on demand
- YAGNI - File I/O fast enough
- Add if profiling shows bottleneck

**No validation beyond Pydantic**: Schema validation sufficient
- YAGNI - Additional validation not needed yet
- Add if proven necessary

**No speculative features**:
- No profile templates/generators
- No profile transformation DSL
- No elaborate validation framework

---

## Future Enhancements

**Only add when proven needed through real usage**:

### Profile Validation API
- **Add when**: Users request validation separate from compilation
- **Add how**: `validate_profile(profile: Profile) -> list[ValidationError]`

### Profile Builder Pattern
- **Add when**: Apps request programmatic profile construction
- **Add how**: Builder API for profile creation

### Caching Layer
- **Add when**: Performance profiling shows loading bottleneck
- **Add how**: LRU cache with path-based invalidation

### Profile Transformation
- **Add when**: Apps request profile manipulation beyond loading
- **Add how**: Transform functions or builder pattern

**Current approach**: YAGNI - ship minimal, grow based on evidence.

---

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

---

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
