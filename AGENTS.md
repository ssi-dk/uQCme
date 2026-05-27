# AGENTS.md
This file provides guidelines for AI agents working on this code.

uQCme is quality control software for data derived from next-generation whole genome sequencing of microbes.
The raw sequences are processed by a variety of third-part tools such as assemblers, assembly QC, plasmid sequence finders and so on. Each of these tools provide metrics, e.g. N50 for assembly. uQCme then gathers arbitrary data from arbitrary sources, together with a config file specifying rules for quality control (e.g. "If the value in column X, from TSV file foo.tsv is below 10, this check failed").

## Commands
This project is managed by Pixi. Use `pixi reinstall` to re-install and `pixi run test` to test.

## General guidelines
* After making changes, run `ruff check .`, address lints and then run `ruff format .`

## Coding guidelines
* Use string typing to lean against the type system where possible.
* Compare `x` against `None` with `x is None`, do not treat it as an implicit boolean (i.e. do not do `not x`).
* When git comitting, the header should be less than 60 characters and lines in the body should be no more than 80 characters.
* Document functions and classes with comments above, not docstrings.

Distinguish un-validated data at the boundary, such as files loaded from YAML files with validated objects.
The former should subclass pydantic's BaseModel, the latter should be a dataclass.

## Agent skills

### Issue tracker

GitHub issues in `ssi-dk/uQCme`; keep issues public-safe and link private
deploy details from the relevant deploy repo. See
`docs/agents/issue-tracker.md`.

### Triage labels

Use the default triage label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo; read root `CONTEXT.md` and `docs/adr/` when present. See
`docs/agents/domain.md`.
