---
last_updated: 2025-10-31
status: stable
audience: user
---

# Agent Authoring Guide

This guide explains how to create and customize Amplifier agents - specialized AI configurations for focused tasks.

**Related Documentation:**
- [System Design](DESIGN.md) - Technical design and implementation
- [Profile Authoring](PROFILE_AUTHORING.md) - Creating profiles that load agents
- [API Reference](../README.md) - AgentLoader and AgentResolver APIs

## Overview

Agents in Amplifier are specialized sub-sessions with:

- **Focused system instructions** - Clear, task-specific guidelines
- **Specific tool subsets** - Only the tools needed for the task
- **Custom models** (optional) - Different models for different needs
- **Partial mount plans** - Override only what's needed, inherit the rest

### How Agents Work

1. Parent session delegates task to agent via task tool
2. System resolves agent file from search locations (first match wins)
3. Agent config (partial mount plan) merges with parent session config
4. Forked sub-session executes with specialized configuration
5. Results return to parent

### File Format and Location

Agents are **Markdown files** with YAML frontmatter stored in:

**Direct agent directories:**
- `amplifier_app_cli/data/agents/` - Bundled agents (shipped with package)
- `.amplifier/agents/` - Project agents (committed to git)
- `~/.amplifier/agents/` - User agents (personal)

**Collection agent directories:**
- `amplifier_app_cli/data/collections/<collection>/agents/` - Bundled collection agents
- `.amplifier/collections/<collection>/agents/` - Project collection agents
- `~/.amplifier/collections/<collection>/agents/` - User collection agents

Agents from collections appear in lists with `collection:name` format (e.g., `design-intelligence:art-director`). See [amplifier-collections](https://github.com/microsoft/amplifier-collections) for details on the collections system.

## Agent Structure

```yaml
---
meta:
  name: agent-name       # Required: unique identifier
  description: "Purpose" # Required: what this agent does

# Optional: Override provider/model
providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main  # Optional
    config:
      model: claude-sonnet-4-5

# Optional: Specify tool subset
tools:
  - module: tool-filesystem
  - module: tool-custom
    source: git+https://github.com/you/custom-tool@main  # Optional: Custom module source
    config:
      api_key: ${CUSTOM_API_KEY}  # Optional: Module config

# Optional: Custom hooks
hooks:
  - module: hooks-logging
    config:
      verbose: true

# Optional: Session config overrides
session:
  orchestrator: loop-streaming
  context: context-simple
---

# Agent System Instruction

You are a specialized agent designed for [specific purpose].

Your focus: [key responsibility]

When working on tasks:
1. [Step 1]
2. [Step 2]
3. [Step 3]
```

### Minimal Agent

The simplest agent needs only metadata and system instruction:

```yaml
---
meta:
  name: simple-helper
  description: "Simple helper for basic tasks"
---

You are a helpful assistant focused on providing clear, concise answers.
```

Inherits everything from parent (tools, providers, hooks, etc.).

### Referencing Shared Context

Agent markdown bodies support @mentions to load shared context files:

```yaml
---
meta:
  name: custom-architect
  description: "Custom design agent with shared foundation"

tools:
  - module: tool-filesystem
  - module: tool-bash
---

@foundation:context/shared/common-agent-base.md

You are a custom architecture specialist.

Additional focus areas:
- Database design
- API contracts
- Performance optimization
```

**@mention types:**
- `@collection:path` - Collection resources (e.g., `@foundation:context/shared/common-agent-base.md`)
- `@user:path` - User directory shortcut (e.g., `@user:context/my-guidelines.md`)
- `@project:path` - Project directory shortcut (e.g., `@project:context/standards.md`)
- `@path` - Direct path relative to CWD (e.g., `@AGENTS.md`, `@ai_context/FILE.md`)

See [API Reference](../README.md#mention-expansion) for complete @mention syntax and [amplifier-collections](https://github.com/microsoft/amplifier-collections) for the collections system.

## Agent Resolution

### Search Order (Highest to Lowest Priority)

Amplifier searches for agents using **first-match-wins**:

1. **Environment variable**: `AMPLIFIER_AGENT_<NAME>=/path/to/agent.md`
2. **User agents**: `~/.amplifier/agents/<name>.md`
3. **Project agents**: `.amplifier/agents/<name>.md`
4. **Bundled agents**: `amplifier_app_cli/data/agents/<name>.md`

**First found wins** - No merging, complete replacement.

### Resolution Examples

**Example 1**: Override bundled agent
```bash
# Bundled: amplifier_app_cli/data/agents/zen-architect.md
# Project: .amplifier/agents/zen-architect.md  (← this one used)
```

**Example 2**: Personal override
```bash
# Bundled: amplifier_app_cli/data/agents/researcher.md
# Project: (none)
# User: ~/.amplifier/agents/researcher.md  (← this one used)
```

**Example 3**: Temporary testing
```bash
export AMPLIFIER_AGENT_BUG_HUNTER=/tmp/test-hunter.md
# Env var always wins (← this one used)
```

## Key Concepts

### Partial Mount Plans

Agents specify only what they override. Everything else inherits from parent:

```yaml
---
meta:
  name: focused-agent
  description: "Focused on documentation"

# Only override tools - everything else inherited
tools:
  - module: tool-filesystem
---

You write clear documentation.
```

**Inherits from parent**: providers, hooks, orchestrator, context, all session config

### How Agent Configs Merge with Parent

Agent configurations merge with parent session configs using **deep recursive merging with module-list-by-ID**:

**Merge Rules:**
- **Module lists** (providers, tools, hooks) merge by module ID (not replaced entirely)
- **Config dicts** merge recursively (child keys override parent keys)
- **Sources inherit** - if parent has module source, agent doesn't need to repeat it
- **Scalar values** override (child replaces parent)

**Example: Module List Merging by ID**

```yaml
# Parent session has:
providers:
  - module: provider-anthropic
    source: git+https://github.com/.../provider-anthropic@main
    config:
      model: claude-sonnet-4-5
      temperature: 0.7

# Agent specifies:
providers:
  - module: provider-anthropic  # Matches by module ID
    config:
      temperature: 0.3  # Override just temperature

# Result after merge:
providers:
  - module: provider-anthropic
    source: git+https://github.com/.../provider-anthropic@main  # Inherited!
    config:
      model: claude-sonnet-4-5      # Inherited
      temperature: 0.3               # Overridden
```

**Key Benefits:**
- **DRY** - Don't repeat sources in every agent
- **Partial overrides** - Change just what you need (like temperature)
- **Deep config merging** - Nested config keys merge recursively

**Same merge logic as profiles** - Agents use the same deep merge implementation as profile inheritance, ensuring consistent behavior throughout the system.

**Implementation**: Uses `amplifier_profiles.merger.merge_profile_dicts()` for all configuration merging.

### Tool Subsets

**Omit tools** → Inherit all parent tools (general purpose):
```yaml
---
meta:
  name: general-agent
  description: "Can use any tool"
# No tools specified → inherits parent's tools
---
```

**Specify tools** → Use only these tools (focused):
```yaml
---
meta:
  name: reader-agent
  description: "Read-only operations"

tools:
  - module: tool-filesystem  # Only this tool
---
```

**Empty tools** → No tools at all:
```yaml
---
meta:
  name: pure-reasoning
  description: "Pure reasoning, no external tools"

tools: []  # Explicit empty
---
```

### Module Configuration

Tools, providers, and hooks use the `ModuleConfig` pattern (same as profiles).

**Each module entry supports:**
- `module` (required): Module ID
- `source` (optional): Where to load module from (git URL, local path, package name)
- `config` (optional): Module-specific configuration

```yaml
providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      model: claude-sonnet-4-5
      max_tokens: 200000

tools:
  - module: tool-web
    source: git+https://github.com/you/forked-web-tool@main  # Use fork
    config:
      timeout: 30
  - module: tool-filesystem  # No source = uses default resolution
```

**Full ModuleConfig support** - Agents can specify module sources just like profiles (git URLs, local paths, packages, etc.).

## Working Examples

### Example 1: Model Specialist

Use different model for complex analysis:

```yaml
---
meta:
  name: deep-analyzer
  description: "Deep analysis with larger model"

providers:
  - module: provider-anthropic
    config:
      model: claude-opus-4-1
      max_tokens: 200000
---

You perform deep, comprehensive analysis of complex systems.

Approach:
1. Understand full context
2. Identify patterns and relationships
3. Provide detailed insights
4. Support conclusions with evidence
```

### Example 2: Tool-Focused Agent

Specialist with specific tool subset:

```yaml
---
meta:
  name: doc-writer
  description: "Documentation writing specialist"

tools:
  - module: tool-filesystem

# Reduce token limit (docs don't need huge context)
session:
  context:
    module: context-simple
    config:
      max_tokens: 50000
---

You write clear, comprehensive documentation.

Guidelines:
- Start with overview
- Provide examples
- Explain concepts clearly
- Cross-reference related docs
```

### Example 3: Security-Enhanced Agent

Additional security layer:

```yaml
---
meta:
  name: secure-executor
  description: "Executes commands with approval requirements"

tools:
  - module: tool-bash
  - module: tool-filesystem

hooks:
  - module: hooks-logging
  - module: hooks-approval
    config:
      patterns: ["rm", "delete", "drop", "truncate"]
---

You execute system commands with security awareness.

Before destructive operations:
1. Explain what will happen
2. List affected resources
3. Wait for explicit approval
```

### Example 4: Custom Orchestrator Agent

Strategic planner with different execution loop:

```yaml
---
meta:
  name: strategic-planner
  description: "Strategic planning with multi-phase approach"

session:
  orchestrator: loop-with-planning

providers:
  - module: provider-anthropic
    config:
      model: claude-opus-4-1
---

You create strategic roadmaps using structured planning.

Process:
1. Understand objectives and constraints
2. Generate multiple strategic options
3. Analyze trade-offs for each option
4. Recommend best path with justification
5. Create phased implementation plan
6. Identify risks and mitigations
```

## Using Agents in Profiles

Agents are loaded via profiles using the `agents` schema:

### Load from Standard Locations

```yaml
# Profile automatically searches standard locations
agents:
  include:
    - zen-architect    # Resolves from search path
    - bug-hunter       # Resolves from search path
    - researcher       # Resolves from search path
```

System searches: user → project → bundled

### Define Inline

```yaml
# Define agent directly in profile
agents:
  inline:
    quick-helper:
      meta:
        name: quick-helper
        description: "Quick inline helper"
      tools:
        - module: tool-filesystem
      system:
        instruction: "You are a quick helper for simple tasks."
```

### Combine Both

```yaml
# Load some from files, define others inline
agents:
  include:
    - zen-architect  # From file (searches standard locations)
  inline:
    project-helper:
      meta:
        name: project-helper
        description: "Project-specific helper"
      # ... config ...
```

## Testing Your Agent

### Validation

```bash
# Validate agent file
amplifier agents validate my-agent.md

# Check where agent resolves from
amplifier agents show my-agent
```

### Testing in Session

```bash
# Start session with profile that loads your agent
amplifier profile use dev

# Delegate to your agent
amplifier run "Delegate to my-agent: test task"
```

### Common Issues

1. **Agent Not Found**
   - Verify file exists in search path
   - Check filename matches agent name
   - Use `amplifier agents list` to see discovered agents

2. **YAML Syntax Errors**
   - Use proper indentation (2 spaces)
   - Quote strings with colons: `description: "Note: something"`
   - Validate with `amplifier agents validate`

3. **Module Not Found**
   - Verify module is installed
   - Check module ID matches exactly
   - Test module works in parent session

4. **Tool Inheritance Issues**
   - Omit `tools:` entirely to inherit all
   - Specify `tools:` to override with subset
   - Use `tools: []` for no tools

## Best Practices

### 1. Start from Bundled Agents

```bash
# Copy bundled agent as template
amplifier agents show zen-architect > ~/.amplifier/agents/my-architect.md

# Edit to customize
# Test thoroughly
```

### 2. Keep Agents Focused

**Good** - Single clear purpose:
```yaml
meta:
  name: doc-writer
  description: "Documentation writing only"
```

**Avoid** - Multiple unrelated purposes:
```yaml
meta:
  name: kitchen-sink
  description: "Writes docs, reviews code, plans architecture, and makes coffee"
```

### 3. Use Tool Subsets Wisely

Give agents only what they need:

```yaml
# Doc writer doesn't need bash or web
tools:
  - module: tool-filesystem

# Researcher needs web and search
tools:
  - module: tool-web
  - module: tool-search
  - module: tool-filesystem
```

### 4. Document Clearly

System instruction should explain:
- What the agent does
- How it approaches tasks
- Any special methods or frameworks
- Limitations or scope

### 5. Version Control Strategy

- **Bundled agents**: Don't modify (override instead)
- **Project agents**: Commit to git (`.amplifier/agents/`)
- **User agents**: Keep local (`~/.amplifier/agents/`)

## Override Strategies

### Override at Project Level

Customize bundled agent for whole project:

```bash
mkdir -p .amplifier/agents

# Start from bundled version
amplifier agents show zen-architect > .amplifier/agents/zen-architect.md

# Customize for project
# Edit: Add project-specific tools, adjust instructions

# Commit
git add .amplifier/agents/zen-architect.md
git commit -m "Customize zen-architect for project needs"
```

### Override for Personal Use

Personal version without affecting project:

```bash
mkdir -p ~/.amplifier/agents

# Start from project/bundled version
amplifier agents show researcher > ~/.amplifier/agents/researcher.md

# Customize for your workflow
# Edit: Adjust to your preferences
```

### Temporary Testing

Test changes without modifying files:

```bash
# Create test version
cp .amplifier/agents/zen-architect.md /tmp/test-zen.md

# Edit /tmp/test-zen.md

# Test with env var
export AMPLIFIER_AGENT_ZEN_ARCHITECT=/tmp/test-zen.md
amplifier run "test task"

# Unset to return to normal
unset AMPLIFIER_AGENT_ZEN_ARCHITECT
```

## CLI Commands

### List Agents

```bash
# See all available agents
amplifier agents list
```

Example output:
```
Available Agents
┌─────────────────────────────────────────┬────────────────────┬──────────────────────────────┐
│ Name                                    │ Source             │ Description                  │
├─────────────────────────────────────────┼────────────────────┼──────────────────────────────┤
│ zen-architect                           │ bundled            │ System design with simplicity│
│ bug-hunter                              │ bundled            │ Systematic debugging         │
│ researcher                              │ bundled            │ Research and synthesis       │
│ design-intelligence:art-director        │ user-collection    │ Aesthetic strategy expert    │
│ developer-expertise:zen-architect       │ bundled            │ Same as zen-architect        │
│ custom-analyzer                         │ project            │ Project-specific analysis    │
└─────────────────────────────────────────┴────────────────────┴──────────────────────────────┘
```

**Source labels:**
- `bundled` - Shipped with amplifier-app-cli
- `user-collection` - From installed collection in `~/.amplifier/collections/`
- `project-collection` - From project collection in `.amplifier/collections/`
- `project` - Direct agent in `.amplifier/agents/`
- `user` - Direct agent in `~/.amplifier/agents/`

### Show Agent

```bash
# Display agent configuration
amplifier agents show zen-architect

# Shows:
# - Agent metadata
# - Resolution path (which file used)
# - Full configuration
# - System instruction
```

### Validate Agent

```bash
# Check agent file is valid
amplifier agents validate my-agent.md

# Checks:
# - YAML syntax
# - Required fields present
# - Module references valid
```

## Advanced Features

### Module Sources in Agents

Agents can specify module sources (like profiles):

```yaml
---
meta:
  name: custom-agent
  description: "Uses forked module"

tools:
  - module: tool-custom
    source: git+https://github.com/you/custom-tool@main
    config:
      api_url: http://localhost:8000
---
```

### Session Config Overrides

Override orchestrator or context for specialized execution:

```yaml
---
meta:
  name: planner
  description: "Strategic planning with planning loop"

session:
  orchestrator: loop-with-planning
  context: context-persistent

providers:
  - module: provider-anthropic
    config:
      model: claude-opus-4-1
      max_tokens: 200000
---
```

### Hook Customization

Add or remove hooks for specific agent needs:

```yaml
---
meta:
  name: silent-processor
  description: "Background processing without UI"

# Remove streaming UI, keep logging
hooks:
  - module: hooks-logging
---
```

### Sub-Agent Access Control

Control which agents this agent can delegate to via its task tool:

```yaml
---
meta:
  name: zen-architect
  description: "Design agent that delegates to builder only"

# Restrict sub-agent delegation (Smart Single Value format)
agents:
  - modular-builder  # Can only delegate to modular-builder
---
```

**Agents field options:**
- **Omit entirely** → Inherit all parent agents (default)
- **`agents: all`** → Explicitly inherit all parent agents
- **`agents: none`** → Disable sub-agent delegation entirely
- **`agents: [name1, name2]`** → Allow delegation only to listed agents

**Example: Design → Build pipeline**

```yaml
---
meta:
  name: zen-architect
  description: "Architecture design, delegates implementation to builder"

agents:
  - modular-builder  # Only this agent available for delegation

tools:
  - module: tool-filesystem
---

You design system architecture with ruthless simplicity.

When implementation is needed, delegate to modular-builder with clear specifications.
Do not delegate to other agents - focus on design only.
```

**Example: Disable delegation entirely**

```yaml
---
meta:
  name: leaf-worker
  description: "Does work directly, no sub-delegation"

agents: none  # Cannot call task tool to delegate

tools:
  - module: tool-filesystem
  - module: tool-bash
---

You complete tasks directly without delegating to other agents.
```

**How it works:**
1. Parent session has agents loaded (from profile)
2. When agent spawns sub-session, its `agents` field filters parent's available agents
3. Sub-session's task tool only sees filtered agents
4. Agent can only delegate to allowed sub-agents

## Common Agent Patterns

### Research Agent

Optimized for information gathering:

```yaml
---
meta:
  name: researcher
  description: "Research and information synthesis"

tools:
  - module: tool-web
  - module: tool-search
  - module: tool-filesystem

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
      max_tokens: 150000
---

You gather, analyze, and synthesize information from multiple sources.

Research methodology:
1. Understand research question
2. Identify relevant sources
3. Extract key information
4. Synthesize findings
5. Provide clear summary with sources
```

### Code Review Agent

Focused on quality assessment:

```yaml
---
meta:
  name: code-reviewer
  description: "Code quality and philosophy compliance review"

tools:
  - module: tool-filesystem
  - module: tool-bash  # For running checks

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
---

You review code for quality, simplicity, and philosophy alignment.

Review framework:
1. Understand purpose and context
2. Check for unnecessary complexity
3. Verify philosophy compliance
4. Identify refactoring opportunities
5. Provide actionable recommendations
```

### Analysis Agent

Read-only analysis without modifications:

```yaml
---
meta:
  name: analyzer
  description: "Code and system analysis"

tools:
  - module: tool-filesystem  # Read only, no modifications
---

You analyze code and systems without making changes.

Analysis approach:
1. Read relevant files
2. Identify patterns and structure
3. Assess complexity and quality
4. Provide insights and recommendations
```

### Builder Agent

Full modification capabilities:

```yaml
---
meta:
  name: builder
  description: "Implementation and code generation"

tools:
  - module: tool-filesystem
  - module: tool-bash

providers:
  - module: provider-anthropic
    config:
      model: claude-sonnet-4-5
---

You implement code from specifications.

Build process:
1. Understand requirements fully
2. Design module structure
3. Implement with tests
4. Verify functionality
5. Document clearly
```

## Troubleshooting

### YAML Syntax Errors

**Common mistake** - Unquoted strings with colons:

```yaml
# ❌ Wrong - causes parser error
description: Note: this will fail

# ✅ Correct - quote strings with colons
description: "Note: this works"
```

**Tip**: If you see `yaml.scanner.ScannerError`, check your description field for unquoted colons.

### Agent Not Loading

```bash
# Check if agent is discovered
amplifier agents list | grep my-agent

# See which file is being used
amplifier agents show my-agent

# Check resolution path
ls ~/.amplifier/agents/my-agent.md
ls .amplifier/agents/my-agent.md
```

### Agent Uses Wrong File

Check resolution order:

```bash
# See which file is actually used
amplifier agents show zen-architect

# Output shows: "Resolved from: ~/.amplifier/agents/zen-architect.md"
```

If wrong file is being used, remove or rename higher-priority files.

### Module Not Found

```bash
# Check module installation
pip list | grep amplifier-module

# Verify module name in agent
amplifier agents show my-agent

# Test module in parent session
amplifier run --profile dev "test"
```

## Best Practices

### 1. Start from Bundled Agents

```bash
# Copy bundled agent as template
amplifier agents show zen-architect > ~/.amplifier/agents/my-architect.md

# Edit to customize
# Test thoroughly
```

### 2. Keep Agents Focused

One clear purpose:
- Documentation writing
- Code review
- Research
- Strategic planning

Not:
- "Everything agent"
- Multiple unrelated tasks
- Overlapping responsibilities

### 3. Use Tool Subsets

Give agents only what they need:
- Doc writer: just filesystem
- Researcher: web, search, filesystem
- Code reviewer: filesystem, bash (for checks)

### 4. Clear System Instructions

Explain:
- Agent's role and expertise
- How it approaches tasks
- Expected workflow or methodology
- Output format

### 5. Test Incrementally

1. Create minimal agent (meta + instruction)
2. Test basic functionality
3. Add tool overrides as needed
4. Test with real tasks
5. Refine based on results

## Summary

Amplifier agents provide specialized execution environments:

- **Markdown format** with YAML frontmatter
- **Partial mount plans** that override parent config
- **First-match-wins resolution** from standard locations
- **Tool subsets** for focused capabilities
- **Model customization** for task-appropriate models
- **Simple override mechanism** via search path

Start with bundled agents (`zen-architect`, `bug-hunter`, `researcher`, `modular-builder`) and customize for your specific needs.

## Related Documentation

**Profile System:**
- [Profile Authoring](PROFILE_AUTHORING.md) - Creating profiles that load agents
- [System Design](DESIGN.md) - Architecture and design decisions
- [API Reference](../README.md) - AgentLoader and AgentResolver APIs

**Amplifier Ecosystem:**
- [Getting Started](https://github.com/microsoft/amplifier) - User onboarding
- [amplifier-collections](https://github.com/microsoft/amplifier-collections) - Collections system
