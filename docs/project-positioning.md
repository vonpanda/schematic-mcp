# Project positioning

`schematic-mcp` is a **hardware context layer for AI coding agents**, not a general-purpose EDA GUI automation server.

Its job is to turn hardware design sources into deterministic, queryable electrical facts that an agent can use while reasoning about firmware and electronics.

## The gap

AI coding agents can read source code well, but embedded software depends on facts that often live somewhere else:

- which physical MCU pin carries a signal;
- which components share a net;
- whether a GPIO macro agrees with the board schematic;
- whether a signal is actually connected, unconnected, or ambiguous;
- which electrical assumptions are supported by the design source rather than inferred from naming conventions.

When those facts remain locked in EDA files, a coding agent may generate perfectly valid software for the wrong hardware connection.

## What this project optimizes for

### 1. Deterministic hardware context

The core parser and graph do not require an LLM call. Given the same EDA source, they should produce the same component/pin/net model every time.

This gives an agent a source of truth it can query instead of asking a model to visually guess connectivity from screenshots.

### 2. File-driven operation

The current KiCad adapter reads `.kicad_sch` source directly. A running KiCad GUI is not required for normal read/query workflows.

That matters for:

- coding-agent sandboxes;
- CI pipelines;
- headless development environments;
- repository review;
- automated firmware validation.

Editor/IPC automation remains useful for interactive editing workflows, but it solves a different problem.

### 3. Vendor-neutral agent contract

EDA-specific parsing is kept behind adapters. MCP tools operate on a canonical model rather than exposing KiCad-specific concepts everywhere.

The intended progression is:

```text
KiCad ---------\
Altium ---------+--> adapter --> canonical electrical graph --> MCP tools --> AI agent
EasyEDA --------+
PDF/vector -----/
```

This makes future cross-EDA support possible without requiring agents to learn a different query API for every vendor.

### 4. Firmware ↔ schematic verification

The project already exposes `validate_pinmap(reference, expected)`.

A firmware tool or agent can extract an explicit GPIO contract and compare it with resolved schematic nets. The synthetic repository demo intentionally swaps two GPIO assignments and the MCP result reports both mismatches.

This is a concrete example of hardware context preventing a source-code-only error.

### 5. Conservative electrical semantics

Unknown information should stay unknown.

The project intentionally avoids:

- inventing nets when connectivity cannot be resolved;
- assuming internal connectivity through an IC;
- silently fuzzy-matching signal names;
- hiding ambiguous pin identifiers;
- treating unsupported EDA constructs as if they were understood.

Warnings, unknown states, and future confidence metadata are preferred over confident fabrication.

## What this project is not

The near-term goal is **not** to:

- replace KiCad or another EDA editor;
- become an autorouter;
- expose hundreds of GUI-editing commands for tool-count alone;
- run arbitrary customer firmware or project scripts;
- require an OpenAI API key for core schematic parsing;
- make an LLM responsible for determining basic electrical connectivity.

Those boundaries keep the project useful as infrastructure that other coding agents, IDEs, CI systems, and EDA integrations can build on.

## Target users

The most relevant early users are:

- embedded developers using AI coding agents;
- hardware/firmware teams reviewing pin contracts;
- MCP host and IDE developers who want hardware context;
- CI systems validating firmware against hardware design sources;
- EDA-tool maintainers who want a format-neutral agent-facing graph;
- open-source hardware projects that want their schematics to be machine-queryable by coding agents.

## Why this can matter to the open-source ecosystem

The value is not limited to one EDA editor. The reusable abstraction is the boundary between **hardware design truth** and **software-agent reasoning**.

A mature version of the project could let an agent answer questions such as:

- “Does this ESP-IDF GPIO configuration match the board?”
- “Which MCU pins are connected to the I2C bus?”
- “Which firmware definitions changed without a corresponding schematic change?”
- “What hardware signals are unresolved or ambiguous before I edit the driver?”
- “Can this hardware repository expose the same query contract even if it migrates from one EDA format to another?”

That is the ecosystem thesis behind `schematic-mcp`: make hardware context a first-class, deterministic input to coding agents.

## Evidence available today

The public repository currently demonstrates this direction with:

- a real modern KiCad S-expression parser;
- a canonical component/pin/net graph;
- MCP tools and resources;
- filesystem boundary enforcement;
- signal tracing and MCU pin maps;
- firmware ↔ schematic pin-map validation;
- synthetic redistributable hardware and firmware fixtures;
- MCP-client end-to-end CI tests;
- Python 3.10/3.11/3.12 CI and package-build verification;
- security, contribution, maintenance, and roadmap documentation.

Adoption metrics should be reported separately and truthfully. Technical capability is not a substitute for real stars, downloads, users, or external contributors.
