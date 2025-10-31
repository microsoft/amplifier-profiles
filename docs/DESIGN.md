---
last_updated: 2025-10-31
status: stable
audience: developer
---

# amplifier-profiles - System Design

This document describes the design and architecture of the amplifier-profiles library, which provides profile and agent loading, inheritance resolution, and Mount Plan compilation.

**Related Documentation:**
- [API Reference](../README.md) - ProfileLoader, AgentLoader, compile_profile_to_mount_plan
- [Profile Authoring](PROFILE_AUTHORING.md) - User guide for creating profiles
- [Agent Authoring](AGENT_AUTHORING.md) - User guide for creating agents

## Purpose

Profiles are reusable, composable configuration bundles that compile to Mount Plans. They provide a simple way to manage complex module configurations and share setups across teams and projects.

Profiles solve several problems:

1. **Reusability**: Define common configurations once, use everywhere
2. **Composition**: Build complex configs from simple pieces via inheritance
3. **Shareability**: Distribute profiles via Git, package managers, or file sharing
4. **Layering**: Apply team and user customizations without modifying base profiles
5. **Simplicity**: High-level YAML frontmatter instead of verbose Mount Plans

## Profile Format

Profiles are Markdown files with YAML frontmatter:

```markdown
# web-dev.md
---
profile:
  name: web-dev
  version: 1.0.0
  description: Web development profile with React tooling
  extends: base  # Optional: inherit from another profile

session:
  orchestrator: loop-streaming
  context: context-persistent
  max_tokens: 200000
  compact_threshold: 0.92

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
      api_key: ${ANTHROPIC_API_KEY}

tools:
  - module: tool-filesystem
    config:
      allowed_paths: ["."]
      require_approval: false
  - module: tool-bash
  - module: tool-web

hooks:
  - module: hooks-logging
    config:
      output_dir: .amplifier/logs
  - module: hooks-backup
---

[Optional system instruction or additional content can go here]
```

### Profile Metadata

The `profile` section contains metadata:

- **name** (required): Unique identifier for the profile
- **version** (required): Semantic version (e.g., "1.0.0")
- **description** (required): Human-readable description
- **extends** (optional): Name of parent profile to inherit from

### Session Configuration

The `session` section specifies core module choices:

- **orchestrator** (required): Which orchestrator module to use
- **context** (required): Which context manager to use
- **max_tokens** (optional): Token limit for context manager
- **compact_threshold** (optional): When to trigger context compaction (0.0-1.0)
- **auto_compact** (optional): Enable automatic compaction (boolean)

### Module Lists

Modules are specified as arrays:

```yaml
providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
  - module: provider-openai
    config:
      model: gpt-5-codex
```

Each module entry has:

- **module** (required): Module ID to load
- **config** (optional): Module-specific configuration dictionary

### Agent Configuration

Agents use a unified schema supporting multiple loading patterns:

```yaml
# Load from directory
agents:
  dirs: ["./agents"]  # Scan for agent .md files

# Load specific agents from directory
agents:
  dirs: ["./agents"]
  include: ["zen-architect", "bug-hunter"]  # Only load these

# Define agents inline
agents:
  inline:
    custom-agent:
      description: "Custom agent"
      providers:
        - module: provider-anthropic
          config:
            model: claude-sonnet-4-5
      tools:
        - module: tool-filesystem

# Combine approaches
agents:
  dirs: ["./agents"]
  include: ["zen-architect"]
  inline:
    extra-agent:
      description: "Additional inline agent"
```

## Directory Structure

Profiles are discovered from multiple locations with increasing precedence. Higher priority locations override lower ones.

### Search Path (Lowest to Highest Priority)

```
1. Bundled Profiles (amplifier-app-cli package)
   amplifier_app_cli/data/profiles/
   ├── foundation.md
   ├── base.md
   ├── dev.md
   ├── production.md
   ├── test.md
   └── full.md

2. Project Profiles
   .amplifier/profiles/
   └── team-standards.md

3. User Profiles
   ~/.amplifier/profiles/
   └── my-custom.md

4. Environment Variables (highest priority)
   AMPLIFIER_PROFILE_<NAME>=/path/to/profile.md
```

### Bundled Profiles

Included with the `amplifier-app-cli` package:

- Shipped with installation (uv, pip, etc.)
- Default configurations maintained by Amplifier team
- Located in package data directory
- Lowest priority - easily overridden

### Project Profiles

Located in `.amplifier/profiles/` within a project:

- Project-specific configurations
- Shared via version control
- Project-wide standards and conventions
- Override bundled defaults for the project
- Can extend any bundled profile

### User Profiles

Located in `~/.amplifier/profiles/`:

- Personal configurations
- Per-user customizations
- Override both bundled and project profiles
- Not committed to version control

### Environment Variables

Temporary overrides for testing:

- `AMPLIFIER_PROFILE_<NAME>=/path/to/profile.md`
- Highest priority - overrides all search paths
- Useful for testing profile changes before committing

## Profile Resolution

When a profile is activated, the system resolves it through several steps:

### 1. Inheritance Chain Resolution

If the profile has an `extends` field, the system:

1. Loads the base profile
2. Recursively resolves its inheritance chain
3. Merges from bottom to top (base → child)

Example:

```markdown
# foundation.md
---
profile:
  name: foundation
session:
  orchestrator: loop-basic
  context: context-simple
---

# base.md
---
profile:
  name: base
  extends: foundation
session:
  max_tokens: 100000  # Adds to foundation
tools:
  - module: tool-filesystem
hooks:
  - module: hooks-logging
---

# dev.md
---
profile:
  name: dev
  extends: base
session:
  orchestrator: loop-streaming  # Overrides base's orchestrator
tools:
  - module: tool-web
---
```

Result: `dev` uses `loop-streaming` (overriding base), inherits filesystem tools and logging hooks from `base`, and adds `tool-web`.

**Note on Markdown Body Inheritance**: The `extends:` field inherits YAML configuration (session settings, module lists) but NOT the markdown body. Each profile's markdown body contains its own instructions. Use @mentions to reference shared instruction files if you want to avoid copy-pasting content across profiles.

### 2. Overlay Application

After resolving inheritance, the system looks for overlays:

1. **Bundled overlay**: `<profile-name>.md` in bundled profiles
2. **Project overlay**: `<profile-name>.md` in project profiles directory
3. **User overlay**: `<profile-name>.md` in user profiles directory

Each overlay is merged with increasing precedence, allowing customization without modifying the base profile.

Example workflow:

```
base.md (bundled)
  → base.md (project overlay)
    → base.md (user overlay)
      → Final configuration
```

### 3. Mount Plan Compilation

The final merged profile is compiled into a Mount Plan dictionary:

```python
# Profile YAML frontmatter
session:
  orchestrator: loop-basic
  context: context-simple

providers:
  - module: provider-mock

# Compiles to Mount Plan
{
    "session": {
        "orchestrator": "loop-basic",
        "context": "context-simple"
    },
    "providers": [
        {"module": "provider-mock"}
    ]
}
```

### 4. Further Merging

After profile compilation, the Mount Plan can be further merged with:

- User settings (`~/.amplifier/settings.yaml`)
- Project settings (`.amplifier/settings.yaml`)
- Local settings (`.amplifier/settings.local.yaml`)
- `--config` file flag
- CLI option overrides
- Environment variables

## CLI Commands

### List Profiles

```bash
amplifier profile list
```

Shows all available profiles from all sources:

```
Available Profiles
┏━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Source   ┃ Description                  ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ foundation │ bundled  │ Absolute minimum foundation  │
│ base       │ bundled  │ Core tools and hooks         │
│ dev        │ bundled  │ Development profile          │
│ production │ bundled  │ Production profile           │
│ test       │ bundled  │ Testing profile              │
│ full       │ bundled  │ All features profile         │
│ my-custom  │ user     │ My custom configuration      │
└────────────┴──────────┴──────────────────────────────┘
```

### Show Profile

```bash
amplifier profile show dev
```

Displays:

1. The profile YAML frontmatter and content
2. The compiled Mount Plan (after inheritance and overlays)

Useful for understanding what a profile actually does.

### Use Profile

```bash
amplifier profile use dev
```

Sets the active profile:

- Writes profile name to `.amplifier/settings.local.yaml` by default
- All subsequent `amplifier run` commands use this profile
- Can be overridden with `--profile` flag
- Supports scope flags: `--local` (default), `--project`, `--global`

```bash
# Set for just you
amplifier profile use dev --local

# Set for whole project
amplifier profile use production --project

# Set globally for all projects
amplifier profile use base --global
```

### Current Profile

```bash
amplifier profile current
```

Shows the active profile and where it's configured from:

- Displays profile name and source (local/project/user/system default)
- Shows resolution chain if overrides exist

### Validate Profile

```bash
amplifier profile validate my-profile.md
```

Checks if a profile file is valid:

- Schema validation
- Module ID references are resolvable
- Inheritance chains are valid
- No circular dependencies

## Using Profiles

### In Command Line

**With active profile:**

```bash
# Set once
amplifier profile use dev

# Use implicitly
amplifier run "Write a hello world program"
```

**One-time override:**

```bash
amplifier run --profile production "Deploy to production"
```

### In Python Code

```python
from amplifier_app_cli.profiles import ProfileLoader, compile_profile_to_mount_plan
from amplifier_core import AmplifierSession, ModuleLoader

# Load and compile profile
loader = ProfileLoader()
profile = loader.load_profile("dev")
overlays = loader.load_overlays("dev")
mount_plan = compile_profile_to_mount_plan(profile, overlays)

# Create session
module_loader = ModuleLoader()
session = AmplifierSession(mount_plan, loader=module_loader)

# Use session
await session.initialize()
response = await session.execute("Hello!")
await session.cleanup()
```

## Creating Custom Profiles

### Simple Profile

Create `~/.amplifier/profiles/my-profile.md`:

```markdown
---
profile:
  name: my-profile
  version: 1.0.0
  description: My custom configuration

session:
  orchestrator: loop-basic
  context: context-simple

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
      api_key: ${ANTHROPIC_API_KEY}
---
```

Use it:

```bash
amplifier profile use my-profile
```

### Extending Bundled Profiles

Build on existing profiles:

```markdown
---
profile:
  name: my-dev
  version: 1.0.0
  description: My development setup
  extends: dev  # Inherit from bundled dev profile

# Add extra tools
tools:
  - module: tool-custom
    config:
      api_url: http://localhost:8000

# Override provider model
providers:
  - module: provider-anthropic
    config:
      model: claude-opus-4-1
      api_key: ${ANTHROPIC_API_KEY}
---
```

### Project Profiles

Create `.amplifier/profiles/project-standards.md` in your project:

```markdown
---
profile:
  name: project-standards
  version: 1.0.0
  description: Project-wide standards and tooling
  extends: dev

session:
  max_tokens: 150000  # Project standard

hooks:
  - module: hooks-project-compliance
    config:
      enforcement_level: strict
---
```

Commit to version control:

```bash
git add .amplifier/profiles/project-standards.md
git commit -m "Add project profile"
```

## Profile Overlays

Overlays allow non-destructive customization of profiles without duplicating them.

### Creating an Overlay

If you want to customize the bundled `dev` profile:

**Option 1: Project-wide customization**

Create `.amplifier/profiles/dev.md`:

```markdown
---
# This overlays the bundled dev profile
session:
  max_tokens: 250000  # Project wants more tokens

tools:
  - module: tool-project-specific
---
```

**Option 2: Personal customization**

Create `~/.amplifier/profiles/dev.md`:

```markdown
---
# Personal customizations to dev profile
providers:
  - module: provider-anthropic
    config:
      model: claude-opus-4-1  # I prefer Opus
---
```

### Overlay Precedence

Given a profile `dev`:

1. Load bundled `dev.md` from package data
2. If `.amplifier/profiles/dev.md` exists, merge it (project layer)
3. If `~/.amplifier/profiles/dev.md` exists, merge it (user layer)
4. Result is the effective configuration

## Environment Variables

Profiles support environment variable expansion using `${VAR}` syntax:

```yaml
providers:
  - module: provider-anthropic
    config:
      api_key: ${ANTHROPIC_API_KEY}
      organization: ${ANTHROPIC_ORG}
      base_url: ${ANTHROPIC_API_URL}
```

Variables are expanded at runtime when the Mount Plan is compiled.

**Undefined variables**: If an environment variable is not set, it expands to an empty string.

## Best Practices

### Profile Naming

- **Bundled profiles**: Single word (e.g., `base`, `dev`, `production`)
- **Project profiles**: Descriptive (e.g., `frontend-dev`, `backend-prod`)
- **User profiles**: Personal preference (e.g., `alice-dev`, `my-research`)

### Version Management

- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes
- Document changes in profile description or comments

### Profile Composition

- Start from bundled base profiles when possible
- Use inheritance (`extends`) for "is-a" relationships
- Use overlays for customization without duplication
- Keep profiles focused - one purpose per profile

### Configuration Scope

- **Bundled**: Minimal, widely applicable, stable defaults
- **Project**: Project standards, shared via git, project conventions
- **User**: Personal preferences, API keys, local paths

### Security

- **Never commit API keys** to version control
- Use environment variables for secrets: `${API_KEY}`
- Store user-specific credentials in `~/.amplifier/profiles/`
- Consider using secret management tools for production

## Advanced Features

### Profile Inheritance Chains

Profiles can form inheritance chains:

```
base → dev → my-dev
```

Each level adds or overrides configuration from its parent.

**Circular dependencies are detected and rejected.**

### Multiple Providers

You can configure multiple providers:

```yaml
providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
  - module: provider-openai
    config:
      model: gpt-5-codex
```

The orchestrator will use them based on its strategy (e.g., fallback, load balancing).

### Conditional Configuration

While profiles don't have built-in conditionals, you can achieve similar effects with:

1. **Multiple profiles**: Create `dev-linux.md` and `dev-windows.md`
2. **Environment variables**: Use `${VAR}` to make configs environment-specific
3. **Overlays**: Apply platform-specific overlays at project or user level

## Troubleshooting

### Profile Not Found

```bash
amplifier profile use my-profile
# Error: Profile 'my-profile' not found
```

**Check**:

- Profile file exists in one of the search paths
- Filename matches profile name (e.g., `my-profile.md`)
- File has correct YAML frontmatter syntax

**Debug**:

```bash
amplifier profile list  # See what profiles are discovered
```

### Invalid Profile

```bash
amplifier profile validate my-profile.md
# Error: Invalid profile: ...
```

**Common issues**:

- Missing required fields (`name`, `version`, `description`)
- Invalid YAML frontmatter syntax
- Circular inheritance
- Non-existent parent profile in `extends`

### Module Not Found

```bash
amplifier run
# Error: Module 'tool-custom' not found
```

**Check**:

- Module is installed (`pip list | grep amplifier-mod`)
- Module ID is correct in profile
- Module search paths include the module location

### Inheritance Issues

If a profile with `extends` doesn't work:

1. Verify parent profile exists: `amplifier profile show <parent>`
2. Check for circular inheritance
3. Ensure parent profile is valid
4. Use `amplifier profile show <your-profile>` to see resolved configuration

## Examples

### Complete Examples

See the bundled profiles in `amplifier_app_cli/data/profiles/` for reference:

- `foundation.md` - Absolute minimum foundation
- `base.md` - Core tools and hooks
- `dev.md` - Development profile
- `production.md` - Production profile with safety
- `test.md` - Testing profile with mock provider
- `full.md` - Kitchen sink with all modules

These profiles ship with the package and serve as templates for your own profiles.

### Migration from Config Files

**Old style** (direct config file):

```markdown
# old-config.md
---
session:
  orchestrator: loop-basic
  context: context-simple
  # ...
---
```

**New style** (using profiles):

```bash
# Use a bundled profile
amplifier profile use foundation

# Or create a custom profile
amplifier profile create my-foundation --extend foundation
# Edit ~/.amplifier/profiles/my-foundation.md
amplifier profile use my-foundation
```

## Related Documentation

**For Users:**
- [PROFILE_AUTHORING.md](PROFILE_AUTHORING.md) - User-friendly guide to creating profiles
- [USER_ONBOARDING.md#quick-reference](USER_ONBOARDING.md#quick-reference) - Complete configuration reference
- [USER_ONBOARDING.md](USER_ONBOARDING.md) - Getting started with profiles

**For Developers:**
- Mount Plan Specification: `amplifier-core/docs/MOUNT_PLAN_SPECIFICATION.md`
- [MODULE_DEVELOPMENT.md](MODULE_DEVELOPMENT.md) - Creating modules
- CLI Reference: `docs/CLI_REFERENCE.md`
