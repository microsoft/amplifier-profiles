---
last_updated: 2025-10-31
status: stable
audience: user
---

# Profile Authoring Guide

This guide explains how to create and customize Amplifier profiles to tailor your AI assistant environment.

**Related Documentation:**
- [System Design](DESIGN.md) - Technical design and implementation of the profile system
- [API Reference](../README.md) - ProfileLoader, AgentLoader, and compilation APIs
- [Agent Authoring](AGENT_AUTHORING.md) - Creating custom agents

## Overview

Profiles in Amplifier are YAML configuration presets that define:

- Provider and model selection
- Orchestrator and context manager settings
- Available tools and hooks
- Agent discovery and filtering
- UI and logging preferences
- Session limits and auto-compaction

### File Format and Location

Profiles are **YAML files** with `.md` extension stored in:

**Direct profile directories:**
- `amplifier_app_cli/data/profiles/` - Bundled profiles (shipped with package)
- `.amplifier/profiles/` - Project profiles (committed to git)
- `~/.amplifier/profiles/` - User profiles (personal)

**Collection profile directories:**
- `amplifier_app_cli/data/collections/<collection>/profiles/` - Bundled collection profiles
- `.amplifier/collections/<collection>/profiles/` - Project collection profiles
- `~/.amplifier/collections/<collection>/profiles/` - User collection profiles

Profiles from collections appear in lists with `collection:name` format (e.g., `foundation:base`, `design-intelligence:designer`). See [amplifier-collections](https://github.com/microsoft/amplifier-collections) for details on the collections system.

## Profile Structure

```yaml
---
profile:
  name: myprofile # Required: unique identifier
  version: "1.0.0" # Required: semantic version
  description: "Purpose" # Required: human-readable description
  model: "provider/model" # Optional: shorthand for provider config
  extends: base # Optional: inherit from parent profile

session:
  orchestrator: loop-streaming # Required: orchestrator module ID
  context: context-simple # Required: context manager module ID
  max_tokens: 100000 # Optional: maximum context tokens
  compact_threshold: 0.8 # Optional: compaction trigger (0.0-1.0)
  auto_compact: true # Optional: enable auto-compaction

orchestrator: # Optional: orchestrator-specific config
  config:
    extended_thinking: true # Example for Claude Sonnet 4.5

agents: # Optional: agent configuration
  dirs: ["./agents"] # Directories to search for .md files
  include: ["zen-architect"] # Filter to specific agents only

context: # Optional: context file loading
  files: ["./docs/*.md"] # Files/globs to load each turn
  max_depth: 5 # @mention recursion depth

providers: # List of provider modules
  - module: provider-anthropic
    config:
      default_model: claude-sonnet-4-5

tools: # List of tool modules
  - module: tool-web
  - module: tool-search
    config: # Optional module-specific config
      max_results: 10

hooks: # List of hook modules
  - module: hooks-logging
    config:
      mode: session-only
      session_log_template: ~/.amplifier/projects/{project}/sessions/{session_id}/events.jsonl
  - module: hooks-redaction
    config:
      allowlist: ["session_id", "turn_id"]
---
# Profile Markdown Body - System Instruction

The markdown body (content after the YAML frontmatter) becomes the system instruction for sessions using this profile.

You can use @mention syntax to load additional context files.

## Basic System Instruction

```markdown
---
profile:
  name: my-profile
---

You are a helpful Python development assistant.

Follow PEP 8 guidelines and use type hints consistently.
```

## System Instruction with @Mentions

```markdown
---
profile:
  name: dev
---

You are an Amplifier development assistant.

Core context:
- @AGENTS.md
- @DISCOVERIES.md
- @ai_context/KERNEL_PHILOSOPHY.md

Work efficiently and follow project conventions.
```

**See**: [API Reference](../README.md#mention-expansion) for complete @mention syntax and features.

## Sharing Instructions with @Mentions

To avoid copy-pasting shared instructions across profiles, use @mentions to reference shared files.

### Using Bundled Shared Context

Reference Amplifier's bundled shared context files:

```markdown
---
profile:
  name: specialized
  extends: foundation:profiles/base.md  # YAML config inherits modules/settings
---

@foundation:context/shared/common-profile-base.md

Additionally, you specialize in database architecture.

Context:
- @AGENTS.md
- @DISCOVERIES.md
```

**@collection:path** resolves to collection resources (searches project → user → bundled collections).

### Using Project Shared Context

Create your own shared files in your project:

```markdown
# Step 1: Create project shared file
# File: .amplifier/shared/team-standards.md
Core team practices...
Coding conventions...

# Step 2: Reference from profiles (CWD-relative)
---
profile:
  name: team-dev
---

@.amplifier/shared/team-standards.md

Project-specific context:
- @AGENTS.md
- @.amplifier/architecture/decisions.md
```

**@path** resolves relative to CWD (where amplifier command runs).

### Benefits

- Single source of truth for shared content
- Update once, affects all profiles
- Explicit and clear what's included
- Can compose multiple shared files

```

## Key Concepts

### Profile Inheritance

Profiles support single inheritance via `extends`. Child profiles can be **partial** - they only need to specify what differs from the parent.

```yaml
profile:
  name: my-dev
  version: "1.0.0"
  description: "Custom dev environment"
  extends: dev # Inherit all settings from dev profile
```

**How merging works:**

The loader merges the entire inheritance chain (parent → child) **before validation**. This means:

1. **Child profiles can be partial** - Required fields can be inherited from parent
2. **Module lists are deep-merged by module ID** - Hooks, tools, providers
3. **Config dictionaries are deep-merged** - You can override just specific config keys
4. **Sources are inherited** - No need to repeat git URLs in child profiles
5. **Scalars override** - Simple values in child replace parent values

**Merge behavior by section:**

```yaml
# Lists (hooks, tools, providers): Merge by module ID
# Parent:
hooks:
  - module: hooks-status-context
    source: git+https://github.com/.../hooks-status-context@main
    config:
      include_datetime: true

# Child (can be partial!):
hooks:
  - module: hooks-status-context
    config:
      git_include_commits: 3  # Add/override just this key

# Merged result:
hooks:
  - module: hooks-status-context
    source: git+https://github.com/.../hooks-status-context@main  # Inherited!
    config:
      include_datetime: true      # From parent
      git_include_commits: 3      # From child

# Dicts (session, ui): Recursive deep merge
# Parent:
session:
  orchestrator:
    module: loop-streaming
    source: git+https://...
    config:
      extended_thinking: true

# Child (partial!):
session:
  orchestrator:
    config:
      max_iterations: 10  # Limit to 10 iterations (-1 = unlimited, default)

# Merged:
session:
  orchestrator:
    module: loop-streaming          # Inherited
    source: git+https://...         # Inherited
    config:
      extended_thinking: true       # Inherited
      max_iterations: 10            # Added (-1 = unlimited, default)
```

**Standard inheritance chain:**

```
foundation → base → dev → your-custom-profile
```

**Key benefits:**

- ✅ Less duplication - focus on what's different
- ✅ Inherit sources automatically - no repeated git URLs
- ✅ Cleaner, more maintainable profiles
- ✅ Deep config customization - override just what you need

### Module Configuration

Tools, providers, and hooks use the `ModuleConfig` pattern:

```yaml
tools:
  - module: tool-filesystem # Module ID (required)
  - module: tool-web
    config: # Module-specific config (optional)
      timeout: 30
      max_retries: 3
```

**Important:** This is a **list** of module configurations, not enable/disable flags.

### Agent Configuration

The `agents` section controls which agents are available:

```yaml
agents:
  # Option 1: Load from directories
  dirs:
    - "./agents"
    - "./custom/agents"

  # Option 2: Filter loaded agents (only these will be available)
  include:
    - zen-architect
    - bug-hunter
```

**Note:** There is no `exclude` field. Use `include` to specify exactly which agents you want.

## Working Examples

### Example 1: Simple Profile (base.md)

```yaml
---
profile:
  name: base
  version: "1.1.0"
  description: "Base configuration with core functionality"
  extends: foundation

session:
  orchestrator: loop-basic
  context: context-simple
  max_tokens: 100000
  compact_threshold: 0.8
  auto_compact: true

tools:
  - module: tool-filesystem
  - module: tool-bash

hooks:
  - module: hooks-redaction
    config:
      allowlist: ["session_id", "turn_id", "span_id"]
  - module: hooks-logging
    config:
      mode: session-only
      session_log_template: ~/.amplifier/projects/{project}/sessions/{session_id}/events.jsonl
---
```

### Example 2: Development Profile (dev.md)

```yaml
---
profile:
  name: dev
  version: "1.2.0"
  description: "Development configuration with full toolset"
  extends: base

session:
  orchestrator: loop-streaming
  context: context-simple

orchestrator:
  config:
    extended_thinking: true

tools:
  - module: tool-web
  - module: tool-search
  - module: tool-task

hooks:
  - module: hooks-streaming-ui

agents:
  dirs:
    - ./agents
---
```

### Example 3: Production Profile with Filtered Agents

```yaml
---
profile:
  name: production
  version: "1.1.0"
  description: "Production configuration optimized for reliability"
  extends: base

session:
  orchestrator: loop-streaming
  context: context-persistent
  max_tokens: 150000
  compact_threshold: 0.9
  auto_compact: true

orchestrator:
  config:
    extended_thinking: true

tools:
  - module: tool-web

# Only load specific agents for production
agents:
  dirs:
    - ./agents
  include:
    - researcher # Only the researcher agent
---
```

## Common Patterns

### Research Profile

Create a profile optimized for research tasks:

```yaml
---
profile:
  name: research
  version: "1.0.0"
  description: "Research and analysis configuration"
  extends: base

session:
  orchestrator: loop-streaming
  context: context-persistent
  max_tokens: 200000 # Large context for documents
  compact_threshold: 0.9
  auto_compact: true

orchestrator:
  config:
    extended_thinking: true # Deep analysis

tools:
  - module: tool-web
  - module: tool-search
  - module: tool-filesystem # Read documents

agents:
  dirs:
    - ./agents
  include:
    - researcher
    - synthesis-master
    - content-researcher

context:
  files: ["./research/context/*.md"]
  max_depth: 10 # Deep reference following
---
```

### Minimal Safe Profile

Create a restricted profile for untrusted contexts:

```yaml
---
profile:
  name: safe
  version: "1.0.0"
  description: "Minimal safe configuration"
  extends: foundation # Start from bare minimum

session:
  orchestrator: loop-basic
  context: context-simple
  max_tokens: 50000 # Limited context
  compact_threshold: 0.5
  auto_compact: true

tools:
  - module: tool-filesystem # Read-only by default

# No agents, minimal capabilities
---
```

### Custom Project Profile

Configure for project standards:

```yaml
---
profile:
  name: project-dev
  version: "2.0.0"
  description: "Project development standards"
  extends: dev

providers:
  - module: provider-anthropic
    config:
      default_model: claude-sonnet-4-5

tools:
  - module: tool-filesystem
  - module: tool-bash
  - module: tool-web
  - module: tool-task

hooks:
  - module: hooks-logging
    config:
      mode: session-only
      session_log_template: ~/.amplifier/projects/{project}/sessions/{session_id}/events.jsonl
  - module: hooks-redaction
    config:
      allowlist: ["session_id", "turn_id", "user_id"]
  - module: hooks-streaming-ui

agents:
  dirs:
    - ./project/agents # Project-specific agents
    - ./agents # Standard agents
  include:
    - zen-architect
    - bug-hunter
    - code-reviewer # Project-specific

context:
  files:
    - "./docs/project-standards.md"
    - "./docs/api-guidelines.md"
  max_depth: 3
---
```

## Testing Your Profile

### Validation Commands

```bash
# Apply and verify profile
amplifier profile use myprofile

# Show current configuration
amplifier profile show

# List available profiles
amplifier profile list

# Test with a simple query
amplifier run --profile myprofile --mode chat
```

### Common Issues

1. **YAML Syntax Errors**

   - Use proper indentation (2 spaces)
   - Lists use `-` prefix

   **When to quote strings:**
   - Always quote if text contains `: ` (colon followed by space)
   - Quote if text starts with special characters (`[`, `{`, `@`, etc.)
   - Simple alphanumeric text can be unquoted

   **Examples:**
   ```yaml
   # ✓ Correct
   description: Simple description works fine
   description: "Note: this requires quotes due to colon"
   description: "Handles: multiple colons: perfectly"

   # ✗ Incorrect
   description: Note: missing quotes causes parser error
   ```

2. **Module Not Found**

   - Verify module is installed
   - Check module ID matches exactly
   - Ensure dependencies are met

3. **Agent Loading Issues**

   - Check directories exist
   - Verify `.md` files have proper format
   - Test `include` filter matches agent names

4. **Inheritance Problems**
   - Parent profile must exist
   - Check for circular dependencies
   - Remember lists replace, not merge

## Best Practices

1. **Start from Existing Profiles**: Extend `base` or `dev` rather than starting from scratch

2. **Use Semantic Versioning**: Track profile changes with version numbers

3. **Document Your Profiles**: Include description and markdown documentation

4. **Test Incrementally**: Add features one at a time and test

5. **Keep Profiles Focused**: Create separate profiles for different purposes

6. **Version Control**: Track profiles in your repository

## Advanced Features

### Dynamic Model Selection

Use the `model` shorthand for quick provider config:

```yaml
profile:
  name: gpt-profile
  version: "1.0.0"
  description: "GPT-5 configuration"
  model: "openai/gpt-5.1" # Shorthand for provider config
```

### Context File Patterns

Load specific documentation automatically:

```yaml
context:
  files:
    - "./docs/**/*.md" # All markdown in docs/
    - "./src/**/README.md" # All READMEs in src/
    - "!./docs/archive/*" # Exclude archive folder
  max_depth: 5
```

### Conditional Tool Configuration

Configure tools based on environment:

```yaml
tools:
  - module: tool-filesystem
  - module: tool-bash
    config:
      allowed_commands: ["ls", "cat", "grep"] # Restrict commands
      working_dir: "./safe-zone"
```

## Summary

Amplifier profiles provide powerful, composable configuration:

- **YAML format** with clear schema
- **Inheritance** for building on existing profiles
- **Module lists** for tools, providers, and hooks
- **Agent filtering** via directories and include lists
- **Session controls** for tokens and compaction

Start with bundled profiles (`foundation`, `base`, `dev`, `production`) and extend them for your specific needs.

**For complete schema specification**, see the [amplifier-profiles README](../README.md#schemas).
