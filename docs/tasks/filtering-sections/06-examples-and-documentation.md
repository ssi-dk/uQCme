# FS-06: Publish examples and user documentation

Status: **Complete**

## Dependency and blocker contract

- **Blocked by:** FS-04 and FS-05.
- **Can start when:** Button behavior, URL/reset semantics, filter composition,
  column locking, and warnings match their automated tests.
- **Unlocks:** FS-07.
- **Reason for the blocker:** Public examples must describe the implemented
  contract, not an earlier draft of the UI.

## Outcome

Bundled and repository examples demonstrate working, synthetic lab-specific
FilteringSections, and public documentation explains the schema and
user-visible behavior accurately.

## Likely file locations

- `input/example/mapping.yaml`
- `src/uQCme/defaults/mapping.yaml`
- `README.md`
- focused parsing/example tests under `tests/unit/`
- `CHANGELOG.md`

Do not edit `docs/researchit-wiki`; it is read-only context during this work.

## TDD sequence

### Red: add failing example-contract tests

Before editing examples, add tests that:

- load each maintained example mapping through the FS-01 parser;
- confirm the example preset resolves against a small synthetic dataframe with
  the documented columns;
- confirm its declared filter produces the documented rows; and
- verify that the default and example schemas use only supported public keys.

These tests should fail because the example mappings do not yet contain the new
section.

### Green: update examples and docs

- Add at least one useful FilteringSection to both maintained mapping examples.
- Use a clearly named synthetic `lab_group` field in the public example
  contract, so deployments can replace it with their own lab/group mapping.
  Keep the remaining display mappings tied to the dashboard's generated QC
  columns and ordinary sample metrics.
- Keep sample names and values synthetic and public-safe. Use lab-specific
  examples such as `LabA view` and `LabB view`, with a synthetic `lab_group`
  field and different display-column sets; do not include private lab data.
- Document all four operators with compact YAML examples.
- Explain `data.mapping` precedence and ordered `QC.mapping` fallback.
- Explain that all preset filters use AND and are applied before manual filters.
- Explain overlapping-manual-filter replacement and preservation of unrelated
  manual filters.
- Explain the `filtering_section` URL parameter, shared links, hard refresh,
  unknown values, and URL encoding of display names.
- Explain “Clear View & Filters,” including selection and Data Preview reset.
- Explain that preset columns lock Data Preview only; other tabs and actions
  retain the full row-filtered data.
- Document missing filter and display column warnings and the valid empty-result
  state.
- Update `CHANGELOG.md` as tasks are completed.

### Refactor

- Keep one canonical schema example in the README and link to maintained full
  mapping examples rather than duplicating long blocks.
- Check terminology against the source plan: use “FilteringSection” for a
  configured named view and “manual filter” for the existing widgets.

## Acceptance criteria

- A maintainer can add another named view using YAML only.
- Every documented example parses and is covered by a test.
- Bundled examples do not depend on private columns, hosts, accounts, or data.
- Documentation matches tested Streamlit behavior and contains no deployment
  instructions.
- Existing mapping content and ordering are preserved except for the deliberate
  new top-level object.

## Verification

```bash
pixi run pytest tests/unit/test_filtering_sections_config.py tests/unit/test_filtering_sections.py tests/unit/test_filtering_sections_examples.py
pixi run ruff check .
pixi run ruff format --check .
git diff --check
```

## Layman's explanation

This task turns the feature into something a bioinformatician can copy and use
without changing Python. The example mapping will show a real named view using
safe sample fields, and the README will explain each rule, what the buttons do,
what is saved in the link, and how reset works. Automated tests keep those
examples from becoming outdated or invalid later.
