# uQCme Application Repository Instructions

This public repository owns uQCme application code, CLI and dashboard
behavior, tests, packaging, releases, and public documentation. It must not
contain private hostnames, accounts, production paths, credentials, private
manifests, or deployment topology.

uQCme is quality control software for data derived from next-generation whole genome sequencing of microbes.
The raw sequences are processed by a variety of third-part tools such as assemblers, assembly QC, plasmid sequence finders and so on. Each of these tools provide metrics, e.g. N50 for assembly. uQCme then gathers arbitrary data from arbitrary sources, together with a config file specifying rules for quality control (e.g. "If the value in column X, from TSV file foo.tsv is below 10, this check failed").

## Scope and context

- Default write scope is this repository only.
- The parent workspace, deploy repository, automation repository, generated
  runtimes, and linked wiki are context-only unless the user or accepted spec
  explicitly expands the scope.
- Escalate to product/workspace scope only when acceptance criteria require a
  coordinated private manifest or shared automation change.
- Before substantial work, read the workspace `../../CONTEXT.md` when
  available and:
  - `docs/researchit-wiki/99_Meta/Agents/Agentic Development Workflow.md`
  - `docs/researchit-wiki/99_Meta/Agents/Local Development Agent Boundary.md`
  - `docs/researchit-wiki/20_Products/uQCme/uQCme Automation.md`
  - `docs/researchit-wiki/20_Products/uQCme/uQCme Deployment.md`

## Commands

This project is managed by Pixi.

- Install/synchronize: `pixi install`
- Reinstall: `pixi reinstall`
- Test: `pixi run test`
- Packaging tests: `pixi run test-packaging`
- Dashboard smoke tests: `pixi run test-dashboard-smoke`

## General guidelines

- Use synthetic or non-sensitive fixtures. Real patient, surveillance,
  genomic, credential, or server output does not belong in the repository,
  tests, issues, or agent conversation.
- After making changes, run `ruff check .`, address lints, and then run
  `ruff format .` when Ruff is available in the active environment. Report the
  reproducibility gap if it is unavailable; do not install tooling or alter the
  lock file incidentally.
- Work locally only. Never connect to or execute anything on a server. Label
  user-run server actions `[USER — SERVER]` and required returned evidence
  `[USER — RELAY]`.

## Coding guidelines

- Use string typing to lean against the type system where possible.
- Compare `x` against `None` with `x is None`; do not treat it as an implicit
  boolean with `not x` when `None` is the intended case.
- When committing, keep the header under 60 characters and body lines at no
  more than 80 characters.
- Document functions and classes with comments above, not docstrings.

Distinguish unvalidated data at the boundary, such as files loaded from YAML,
from validated domain objects. The former should subclass Pydantic's
`BaseModel`; the latter should be a dataclass.

## Agent skills

### Task tracking

Read [shared workflow](docs/agents/shared-workflow.md) first, then
[repository tracker settings](docs/agents/issue-tracker.md). Both wiki and
GitHub are supported. Triage labels apply to GitHub-owned tasks only; see
`docs/agents/triage-labels.md` when using that tracker.

### Domain docs

Single-context repo; read root `CONTEXT.md` and `docs/adr/` when present. See
`docs/agents/domain.md`.

## Shared workflow

Before routing work, read [Shared Repository Workflow](docs/agents/shared-workflow.md)
for preferences, wiki/GitHub tracking, authorship, and execution boundaries.
Read [repository tracker settings](docs/agents/issue-tracker.md) for local mappings.
The shared file is wiki-owned and hardlinked here; see [the link contract](docs/HARDLINKS.md).
