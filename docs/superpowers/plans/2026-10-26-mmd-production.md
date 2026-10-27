# MMD Production Implementation Plan

> **For agentic workers:** Execute inline in the authorized current session. Use executing-plans task tracking and verification-before-completion. User approval of the design is already recorded; continue without another design gate.

**Goal:** Install the Blender tool bridge and provide reusable Codex MMD production guidance grounded in text documentation and actual runtime behavior.

**Architecture:** Keep the third-party bridge and add-ons outside tracked source. Add a workflow Skill to the existing plugin, update existing import/check Skills, and document versions and real verification results.

**Tech Stack:** Windows PowerShell, Python 3.11, Blender 4.5.15 LTS, MMD Tools 4.5.14, Blender MCP 1.19.0, optional MMD Tools Append 4.5.13.

## Global Constraints

- Reuse `C:\workspace\blender-mmd-codex` and its existing portable Blender.
- Use search engines, project documentation and text/image tutorials; do not use Bilibili videos for this pass.
- Preserve unrelated Codex settings, Blender preferences and open user scenes.
- Use only original synthetic verification assets. Keep third-party packages, local paths, generated media and environments out of Git.
- Version support claims and visual quality claims must match observed evidence.

## Task 1: Tool bridge and optional add-on

- [x] Inspect pinned Blender MCP installer and runtime entry points.
- [x] Install bridge dependencies and Blender extension from pinned release assets; use the same tag's source build if release downloads fail.
- [x] Download MMD Tools Append from its maintained project's fixed release, inspect package metadata, install and enable it.
- [x] Back up existing Codex config if present, add only `blender_mcp`, disable its telemetry, and install its upstream Skill.
- [x] Verify versions, enabled preferences, MCP initialization and actual scene read/write in an isolated Blender process.

## Task 2: MMD workflow Skills

**Files:** Create `skills/mmd-production/SKILL.md` and focused `references/{asset-research,blender-operations,render-output,learning-sources}.md`. Modify `skills/vmd-workflow/SKILL.md`, `skills/mmd-model-check/SKILL.md`, `.codex-plugin/plugin.json`, and `README.md`.

- [x] Write the coordinator, version-sensitive operator recipes, distribution research process and rendering/output flow.
- [x] Replace outdated planning-only VMD guidance with delegation to the installed MMD Tools; keep unsupported claims explicit.
- [x] Update plugin metadata and README capability descriptions.
- [x] Validate every changed Skill and local reference; install the project's Skills for Codex discovery without overwriting unrelated skills.

## Task 3: Actual verification and handoff

- [x] Create original small PMX, model VMD and camera VMD fixtures in the chat's work directory using MMD Tools data structures.
- [x] Import them through the bridge, read back object/action/camera state, and save a new `.blend`.
- [x] Render a short low-resolution clip, inspect representative frames and encode/decode the video; preserve the result in the chat's outputs folder.
- [x] Save concise setup and verification records in `docs/`, state what has not been established, and inspect the repository diff.
