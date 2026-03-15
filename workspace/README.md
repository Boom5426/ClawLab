# Workspace Schema

This directory stores researcher-specific state and generated artifacts. The current CLI MVP uses local JSON plus markdown files only.

## Top-level directories

- `profile/`
  - `profile.json`: current `ResearcherProfile`
- `projects/`
  - `<project_id>/project.json`: current `ProjectCard`
  - `<project_id>/outputs/`: generated draft markdown files
  - `<project_id>/materials/`: saved `MaterialSummary` files used by tasks
  - `<project_id>/assets/`: project-scoped copies of learned assets
  - `<project_id>/notes/`: project-scoped markdown notes derived from learning
- `assets/`
  - `<asset_id>.json`: global reusable asset records
  - `assets.json`: reverse chronological asset index
  - `writing-rules/*.md`: human-readable writing rules
  - `templates/*.md`: human-readable structure templates
  - `project-notes/*.md`: human-readable project notes
- `tasks/`
  - `<task_id>/task.json`: stored `TaskCard`
  - `tasks.json`: reverse chronological task index

## Current conventions

- File paths stored inside task cards are repo-relative when possible.
- Task cards store both `input_material_paths` and `input_material_types`.
- Task cards may store `material_summary_path` and `material_summary_title`.
- `assets.json` and `tasks.json` are append-latest indexes for fast CLI status reads.
- Project asset copies are duplicated intentionally so each project remains inspectable in isolation.
- Reusable assets are saved both as JSON and markdown so they stay scriptable and human-editable.

## Extension guidance

- Add schema migrations only when a real format change is needed.
- Keep profile / project / task / asset as the four stable top-level concepts.
- If a future LLM is added, keep these persisted JSON contracts stable and swap service internals first.
