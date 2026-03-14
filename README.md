# ClawLab

ClawLab is a Python-first CLI research collaboration system for graduate students and PhD researchers. It turns a local repository into a working research workspace: ingest profile context, define the active project, read research materials, generate a draft for a real task, learn from revision, and accumulate reusable assets over time.

The current stage is deliberately narrow. This repository is not a web app, not a generic agent demo, and not a database-backed platform. It is a local, inspectable, file-based research workbench.

## Current core goal

The current MVP exists to prove one closed loop:

1. initialize a workspace
2. ingest a CV
3. create the current project
4. read research material from `txt`, `md`, or `pdf`
5. run a task such as `literature-outline` or `paper-outline`
6. generate a markdown draft
7. let the user revise the draft manually
8. learn from the revision
9. show the remembered state clearly with `status`

If that loop is reliable, the repository can evolve into a durable research workflow store with SOPs, writing rules, templates, and project memory.

## Repository structure

```text
clawlab/
  cli/
    main.py
  core/
    constants.py
    models.py
  services/
    ingest_service.py
    profile_service.py
    project_service.py
    draft_service.py
    learning_service.py
    workspace_service.py
  storage/
    filesystem.py
  prompts/
  templates/
    drafts.py
  utils/
    ids.py
    text.py
examples/
  cv.txt
  cv_sample.pdf
  project_brief.md
  task_input.txt
  revised_outline.md
  material_sample.pdf
  material_sample_source.ps
workspace/
  README.md
  profile/
  projects/
  assets/
  tasks/
tests/
README.md
pyproject.toml
```

### What each top-level area means

- `clawlab/`: core application code
- `workspace/`: local working state and generated artifacts
- `examples/`: minimal reproducible example files
- `tests/`: standard-library `unittest` coverage

## Supported input types

### CV ingest

- `.txt`
- `.md`
- `.rst`
- `.pdf`

### Task material input

- `.txt`
- `.md`
- `.pdf`

PDF support uses local text extraction through `pdftotext`. This MVP only supports text extraction, not OCR. If a PDF contains no extractable text, the command fails with a clear message.

## CLI commands

### `clawlab init`

Creates:

- `workspace/profile/`
- `workspace/projects/`
- `workspace/assets/`
- `workspace/tasks/`
- `clawlab.json`

### `clawlab ingest-cv <path>`

Reads a CV file, parses it into a `ResearcherProfile`, and saves:

- `workspace/profile/profile.json`

### `clawlab project create`

Interactively asks:

- 你当前最重要的研究项目是什么？
- 你近期最想推进的成果是什么？
- 你当前最卡的是哪一步？
- 你手头有哪些材料？

Then creates the active project directory and `project.json`.

### `clawlab task run <task_type> --project <project_id> --input <path>`

Supported `task_type` values:

- `literature-outline`
- `paper-outline`

The command reads the material file, extracts text, generates a markdown draft, and writes a `TaskCard` that records:

- input material paths
- input material types
- generated draft path

### `clawlab learn --task <task_id> --revised <path>`

Reads the generated and revised drafts, derives:

- 1 to 3 `writing_rule` assets
- 1 `structure_template` asset
- 1 `project_note` asset

Then updates:

- `workspace/tasks/<task_id>/task.json`
- `workspace/assets/*.json`
- `workspace/projects/<project_id>/assets/*.json`
- the active `project.json`

### `clawlab status`

Shows:

- current profile summary
- active project summary
- latest task
- latest task material paths and types
- latest learned assets

## Local setup

Requirements:

- Python 3.11+
- `pdftotext` available on the system path

Install the package in editable mode:

```bash
python3 -m pip install --user -e . --no-build-isolation
```

Or run without installation:

```bash
python3 -m clawlab.cli.main --help
```

## Minimal closed-loop example

1. Initialize the workspace:

```bash
clawlab init
```

2. Ingest the CV:

```bash
clawlab ingest-cv examples/cv.txt
```

You can also ingest a PDF CV:

```bash
clawlab ingest-cv examples/cv_sample.pdf
```

3. Create the project:

```bash
clawlab project create
```

4. Run a task with text input:

```bash
clawlab task run literature-outline --project <project_id> --input examples/task_input.txt
```

5. Or run a task with PDF input:

```bash
clawlab task run paper-outline --project <project_id> --input examples/material_sample.pdf
```

6. Revise the generated markdown file manually, then learn:

```bash
clawlab learn --task <task_id> --revised examples/revised_outline.md
```

7. Inspect current state:

```bash
clawlab status
```

## What the current MVP is designed to persist

### Researcher profile

- name
- role
- discipline
- subfield
- methods
- tools
- writing preferences
- collaboration preferences

### Project state

- active project title and question
- current goal
- blockers
- listed materials
- next step

### Task state

- task type
- input summary
- input material paths
- input material types
- generated draft path
- revised draft path
- learning summary

### Reusable assets

- writing rules
- structure template candidates
- project notes

## Built-in verification

Run:

```bash
python3 -m unittest discover -s tests
```

## Current limitations

This MVP does not yet support:

- OCR for scanned PDFs
- DOCX or HTML material parsing
- databases
- remote APIs or web retrieval
- multi-project orchestration workflows
- autonomous agent runtimes

The current priority is simpler: keep the CLI loop clear, local, inspectable, and useful for real research drafting work.
