# MMD production Skill design

Approved by the user on 2026-10-26, following the design presented in this chat.

## Goal

Guide Codex through tools to make editable MMD animation in Blender: find distribution pages, organize permitted assets, import models/motions/cameras, adjust a scene and camera, render previews, and export video.

## Components

- Blender 4.5.15 LTS portable; MMD Tools 4.5.14 handles PMX/PMD, VMD and VPD.
- Blender MCP by newo-ether, pinned to v1.19.0, supplies live scene inspection and Blender Python execution. Keep it as an external dependency, with telemetry disabled for this local setup.
- MMD Tools Append v4.5.13 is an optional helper for catalog assets, rendering presets, materials and rigs. Its catalog is not an internet-wide distribution search engine.
- Add `mmd-production`, a concise coordinator with references for asset research, imports, previews/output and learning from text documentation. Extend the existing `vmd-workflow` and `mmd-model-check` to use the installed MMD Tools.
- Install the skills so subsequent Codex turns can discover them. Preserve the repository as their editable source and document the installed copies.

## Workflow

Identify the requested output and available assets. Search original distribution pages when needed, retain source/author/terms and distinguish unavailable downloads from found pages. Keep asset folder structure. Inspect the intended Blender instance, import with explicit compatible scale and target selection, inspect actions and camera state, then make requested adjustments. Render a short inexpensive preview before a full animation; save image sequences for recoverable final rendering and encode the result with audio when supplied. Save new `.blend` checkpoints.

## Limits and failure handling

Installation does not establish artistic quality. This first pass verifies the bridge and file import/output primitives with original synthetic fixtures; real character shading, physics, motion compatibility, resource availability and visual quality require an actual production task. Do not substitute rendered video for original VMD data. Use current runtime operator schemas instead of copying obsolete Blender 2.x interface instructions. Keep credentials and third-party assets out of Git.

## Acceptance

- Installed components report their actual versions and enabled state.
- A real MCP stdio client discovers tools, selects an isolated Blender instance, changes a scene and reads it back.
- An original PMX fixture and model/camera VMD fixtures are imported via MMD Tools; changes are measurable across frames.
- A small animation and saved `.blend` are produced and inspected; verification reports distinguish technical success from visual assessment.
- Skills pass frontmatter validation, all local references resolve, and setup instructions reflect the installed state.
