# Oblique Rust Rewrite Roadmap (Incremental, 100% Port)

## Goal

Port Oblique fully from Python to Rust with no big-bang rewrite, while improving:

1. Agentic coding reliability (strong typing, explicit contracts, deterministic errors).
2. Agentic patch creation (machine-friendly patch schema + stable generation targets).
3. Runtime safety and predictability (especially in render/audio/control loops).

## Constraints

1. No long-lived "rewrite branch that never ships."
2. Migrate one subsystem at a time, always with runnable parity checkpoints.
3. Preserve existing user-visible behavior unless explicitly changed.
4. Keep GLSL shaders and visual output parity as first priority.
5. Defer optional architecture pivots (for example OpenGL -> wgpu) until parity is achieved.

## Migration Principles

1. Vertical slices over horizontal rewrites.
2. Every slice must end in a shippable state.
3. Existing Python behavior is the reference spec.
4. Add parity tests before rewriting subsystem internals.
5. Keep interfaces explicit and machine-readable for agents.

## Target End State

1. `oblique` CLI implemented in Rust (`start`, `live`, `render`, `list-modules`, `describe`).
2. Runtime/render loop, headless renderer, IO stack, processing operators, and module system in Rust.
3. Patch authoring that is agent-friendly:
   1. Typed patch schema (JSON/TOML/RON) with validation.
   2. Rust-native DSL for hand-authored advanced patches.
   3. Tooling to scaffold patches/modules with predictable structure.
4. Python runtime removed from the execution path (optional compatibility converter can remain).

## Phase Plan

## Phase 0 - Baseline and Parity Harness (No Rust Runtime Yet)

Deliverables:

1. Golden fixtures:
   1. Reference patches from `projects/demo`.
   2. Fixed audio samples.
   3. Golden frame hashes/stats from `oblique render --inspect`.
2. CLI behavior snapshots for `list-modules` and `describe`.
3. Latency/throughput baseline (fps, frame time, audio callback behavior).

Exit criteria:

1. Baseline CI job runs on every PR.
2. We can detect regressions automatically before any Rust port starts.

## Phase 1 - Rust Workspace and Contracts

Deliverables:

1. Cargo workspace with initial crates:
   1. `oblique-contracts` (schemas, IPC/event contracts, error codes).
   2. `oblique-core` (shared types and module traits).
   3. `oblique-cli` (command skeleton and argument compatibility).
2. Stable, versioned contracts for:
   1. Patch graph representation.
   2. Parameter metadata.
   3. Telemetry/log events.

Exit criteria:

1. Rust CLI parses current command shapes.
2. Contract tests pass against recorded Python outputs.

## Phase 2 - Headless Rendering First (Highest Leverage, Lowest UI Risk)

Deliverables:

1. Rust headless renderer that can render a single frame from a patch graph spec.
2. Shader preprocessor parity (`#include` behavior, LYGIA include resolution).
3. Shader cache and texture cache parity (including fallback-on-compile-failure behavior).

Exit criteria:

1. `render --t ... --inspect` parity for agreed demo patches.
2. Frame stats/hashes within tolerance bounds defined in Phase 0.

## Phase 3 - IO + Processing Stack Port

Deliverables:

1. Audio device input in Rust.
2. Audio file input in Rust.
3. MIDI input in Rust.
4. Processing operators in Rust (`FFTBands`, envelope, spectral metrics, etc).

Exit criteria:

1. Operator outputs match Python baselines within tolerance.
2. No regressions in latency/throughput checkpoints.

## Phase 4 - Module Runtime + Chain API Port

Deliverables:

1. Rust module trait + registry with metadata parity.
2. TexturePass traversal and ping-pong behavior parity.
3. Chain composition features equivalent to `.to()` / `.mix()`.
4. `list-modules` and `describe` from Rust runtime.

Exit criteria:

1. Representative built-in modules render correctly through Rust runtime.
2. Chain API parity scenarios pass from baseline suite.

## Phase 5 - Live Mode and Control Surface

Deliverables:

1. Rust `live` runtime loop.
2. Rust control surface and typed IPC bridge.
3. Hot reload strategy with explicit guardrails and fallback behavior.

Exit criteria:

1. Live parameter editing, telemetry, and reload workflows match baseline behavior.
2. Manual smoke tests for stage-critical flows pass.

## Phase 6 - CLI Cutover and Python Runtime Retirement

Deliverables:

1. Rust becomes default runtime for all primary CLI commands.
2. Optional patch conversion path for legacy Python patches.
3. Deprecation docs and migration notes.

Exit criteria:

1. All phase gates pass in CI.
2. Python runtime no longer required for normal operation.

## Anti-Goose-Chase Guardrails

1. One major subsystem per milestone PR series.
2. No simultaneous renderer backend migration and behavioral port.
3. Each milestone has explicit stop/go criteria before starting the next.
4. Feature flags for unfinished Rust paths; default stays stable.
5. Keep old path available until parity passes for that slice.
6. Weekly risk review with a strict "drop or defer" policy for non-essential work.

## Agentic Coding and Patch Creation Enhancements (Built Into Migration)

1. Contract-first interfaces:
   1. Typed patch schema and strict validation errors.
   2. Stable error codes and structured diagnostics.
2. Generator-friendly scaffolding:
   1. `oblique new module ...`
   2. `oblique new patch ...`
3. Deterministic formatting/linting for generated code and patch specs.
4. Compatibility checker:
   1. "Can this patch run?"
   2. "Which params are invalid/missing?"
5. Patch conformance tests that run in CI for generated artifacts.

## Suggested Milestone Order (Concrete Incremental Sequence)

1. Baseline fixtures + parity CI.
2. Rust contracts crate + CLI parser compatibility.
3. Rust headless single-frame render.
4. Rust shader include/preprocess parity.
5. Rust frame analysis parity.
6. Rust audio file input + selected processing operators.
7. Rust module registry + `list-modules`/`describe`.
8. Rust chain API parity (`to`/`mix` equivalent).
9. Rust live control/IPC parity.
10. Full CLI cutover + Python runtime retirement.

## Done Criteria for the Rewrite

1. 100% of runtime functionality is available from Rust commands.
2. Baseline parity suite passes for agreed patch set and diagnostics.
3. Agent-generated patches can be validated and executed through Rust-native tooling.
4. Migration docs are complete and Python runtime path is formally deprecated.
