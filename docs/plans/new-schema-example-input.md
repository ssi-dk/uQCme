# New-Schema Example Input Plan

## Status

**Complete — 2026-08-18**

- A public synthetic fixture now uses the new export column schema while
  preserving the existing pretend sample names and metric values.
- The repository root `config.yaml` now uses the new-schema example input for
  local development. Packaged defaults and legacy regression fixtures remain
  unchanged.
- Lab groups are transferred by exact `sample_name` identity from the old
  fixture. They are not inferred from species, QC outcomes, or metrics.
- The new fixture contains deterministic direct matches, explicit alias cases,
  mismatches, and missing `rMLST_match` values for visible Sample Details
  coverage.
- The local example mapping uses `species` for the provided/category species
  and `rMLST_match` for the detected program result. QC species rules continue
  to resolve to `species`.
- Real export rows and sensitive data were not copied into the repository. The
  maintained schema manifest contains column names only.
- Current validation passed: 196 tests, 3 dashboard smoke tests, and
  `git diff --check`. Ruff remains unavailable in the active environment and
  was not installed or added to the lock file.

## Layperson's summary

The old pretend dataset and the new real export do not have the same columns.
Instead of changing historical fixtures and risking old regression tests, the
repository now has a second pretend dataset. It keeps the same sample names,
lab groups, and useful test metrics, but presents them using the new export's
columns.

This lets the local Streamlit dashboard exercise the current input shape. The
dashboard still reads ordinary tabular data and mapping configuration; it does
not need a special code path for “old” versus “new” data. The mapping tells
Streamlit which column is the provided species and which column is the
detected result.

## Architecture decision: schema adaptation in fixtures and mapping

The new-schema change belongs at the public fixture and configuration boundary,
not inside the dashboard renderer. This keeps the application
Streamlit-first: Streamlit receives a normal dataframe, applies the existing
filters, and renders the configured fields using native controls and layout.

The generator is responsible for converting the old synthetic source rows into
the public new-schema fixture. It is deterministic and checked into the
repository so a contributor can reproduce the data without access to a real
export. Python code does not guess how production species names relate; those
decisions remain explicit in the mapping YAML and are used by Sample Details.

The old fixture remains a compatibility and regression resource. The new
fixture is the local development default only. Generated runtimes outside this
repository must be regenerated separately before they can see the new input or
mapping.

## Handoff context

This plan applies to the public `uQCme` repository. Relevant files are:

- `config.yaml`
  - Local default configuration pointing to the new-schema input and output.
- `input/example/run_data_new_schema.tsv`
  - Public synthetic input using the new export schema.
- `input/example/mapping.yaml`
  - Local mapping for new column names, species roles, aliases, and lab views.
- `tests/fixtures/new_schema_columns.txt`
  - Canonical public column-name manifest for the new export shape.
- `tests/fixtures/generate_new_schema_fixture.py`
  - Reproducible generator based on the old public synthetic fixture.
- `tests/fixtures/config_new_schema.yaml`
  - Test configuration for regenerating the processed new-schema output.
- `tests/fixtures/new_schema_example_run_data.tsv`
  - Tracked processed output with deterministic QC results.
- `tests/unit/test_new_schema_fixture.py`
  - Schema, identity-transfer, mapping, and deterministic-output coverage.

The legacy resources remain intentionally unchanged:

- `input/example/run_data.tsv`
- `tests/data/example_run_data.tsv`
- `tests/uQCme_example_run_data.tsv`
- `tests/fixtures/config_example.yaml`

## Approved product decisions

- Use the new export header as the canonical schema for the local synthetic
  fixture.
- Preserve every old pretend `sample_name` exactly and preserve the old
  synthetic metric values wherever an equivalent new field exists.
- Omit old-only fields such as `provided_species` when they are not present in
  the new export schema.
- Include new export fields needed by local dashboard behavior and tests,
  including `rMLST_match`, `rMLST_support`, Bracken fields, MLST fields, Quast
  fields, fastp fields, and other manifest columns.
- Keep `species` as the provided/category field.
- Keep `rMLST_match` as the detected program field for Sample Details.
- Keep QC species-rule selection mapped to `species`; `rMLST_match` must not
  silently change QC rule semantics.
- Keep curated naming differences in `SpeciesAliases`, with the direction
  provided/category species → accepted detected values.
- Preserve the existing LabA/LabB assignments by exact sample-name join.
- Fail fixture generation when a source sample is duplicated, has no lab
  group, or cannot be transferred by the identity key.
- Do not add a new runtime flag, schema mode, dashboard component, JavaScript
  layer, or CSS system for this fixture adaptation.
- Keep Streamlit responsible for filtering, table display, and Sample Details;
  use the data and mapping files to provide the fields it already knows how to
  render.

## Implementation plan

### 1. Record the public new-schema contract

- Store the new export's column names in
  `tests/fixtures/new_schema_columns.txt`.
- Keep the manifest limited to schema names. Do not commit real export rows,
  identifiers, surveillance data, or other sensitive values.
- Exclude the dashboard-only `Select` column from the fixture manifest. It is
  created by the Streamlit data editor at display time rather than being an
  input field.
- Validate that manifest columns are non-empty and unique before generation.

### 2. Generate the synthetic new-schema input

- Read the old public synthetic fixture as the source of sample identity,
  existing test values, and lab-group assignments.
- Validate that `sample_name` is unique and that every source row has a
  non-blank `lab_group`.
- Build one output row per source row, preserving source order and all sample
  names.
- Transfer `lab_group` by exact `sample_name`. Do not infer a group from any
  other field.
- Map equivalent old metric columns into their new export names where the
  local fixture needs them, and leave unsupported fields blank or synthetic as
  appropriate.

### 3. Add deterministic species demonstration values

- Use direct values for most rows so ordinary exact matching is visible.
- Use category abbreviations such as `E. coli`, `K. pneumoniae`, and
  `Salmonella` with full `rMLST_match` values to demonstrate configured
  aliases.
- Include deliberate mismatches and a missing detected value to demonstrate
  red status in Sample Details.
- Populate `rMLST_support` and representative Bracken/MLST fields without
  copying real program output.
- Keep all values deterministic so regeneration produces byte-identical TSV
  output.

### 4. Keep mapping and QC semantics explicit

The local example mapping uses the following contract:

```yaml
Provided Species:
  data:
    mapping: species
  QC:
    mapping:
      - speciesName
      - genusName
      - Marker lineage

Expected species:
  data:
    mapping: rMLST_match
  report:
    filter: true
```

- `species` supplies the category/provided value used by QC species rules.
- `rMLST_match` supplies the detected value used by Sample Details.
- `SpeciesAliases` supplies only explicitly reviewed biological equivalences.
- Filtering sections use columns present in the new schema, including
  `Average_Coverage` for the LabB view.
- No new Streamlit code is required to distinguish the two fixture shapes;
  mapping resolution remains the source of truth.

### 5. Make the new fixture the local default

- Point the repository root `config.yaml` at
  `input/example/run_data_new_schema.tsv`.
- Generate the root processed output through the normal CLI workflow so the
  dashboard can load QC results from the new-schema fixture.
- Keep `config_example.yaml`, legacy input fixtures, and packaged defaults
  unchanged for regression and release compatibility.
- Regenerate external/local runtime copies only through their normal runtime
  workflow. A browser refresh cannot copy source-repository changes into a
  separate generated runtime.

## Tests and acceptance criteria

The change is accepted when:

- The new fixture header exactly matches the maintained public manifest.
- Every legacy pretend sample name appears exactly once in the new fixture.
- LabA/LabB assignments match the old fixture by exact `sample_name` join.
- `provided_species` is absent from the new-schema fixture when absent from the
  source export.
- Required rMLST, Bracken, MLST, Quast, fastp, and other new-schema columns are
  present.
- Regeneration is deterministic and produces identical bytes.
- The processed new-schema fixture contains regenerated QC outcome, action,
  failed-rule, and passed-rule columns.
- QC species rules resolve to `species`, never implicitly to `rMLST_match`.
- The local LabA and LabB filtering sections resolve against available new
  columns.
- Sample Details can render every new-schema sample, including direct matches,
  configured aliases, mismatches, and missing detected values.
- The detected species remains a Sample Details presentation field and is not
  added to the navigation table.
- Legacy integration tests and legacy fixture behavior remain unchanged.
- Streamlit remains the primary dashboard renderer; no new custom component or
  schema-specific UI path is introduced.

Run from the repository root:

```bash
pixi run test
pixi run test-dashboard-smoke
ruff check .
ruff format .
git diff --check
```

If Ruff is unavailable in the active environment, report that reproducibility
gap rather than installing it or changing the lock file.

## Out of scope

- Committing real export rows or sensitive data.
- Replacing or deleting legacy fixtures.
- Inferring lab groups, aliases, or species equivalence automatically.
- Fuzzy, substring, abbreviation, or automatic species matching.
- Changing QC rules to use `rMLST_match`.
- Adding a runtime schema-mode flag or a separate dashboard code path for the
  new fixture.
- Updating generated external runtimes as part of a public repository change.
