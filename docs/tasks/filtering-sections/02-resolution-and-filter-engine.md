# FS-02: Resolve fields and apply preset filters

Status: **Not started**

## Dependency and blocker contract

- **Blocked by:** FS-01.
- **Can start when:** Typed FilteringSection models and their parsing tests are
  green.
- **Unlocks:** FS-03.
- **Downstream contract:** Return a resolved runtime object that FS-03, FS-04,
  and FS-05 can consume without reopening raw YAML dictionaries.

## Outcome

Pure, Streamlit-independent code resolves configured fields against a loaded
dataframe and applies all supported preset filters safely. It reports whether a
preset is usable, which display columns remain, and which warnings should be
shown.

## Likely code and test locations

- Add a module such as `src/uQCme/core/filtering.py`.
- Use dataclasses for resolved filters and resolved FilteringSections because
  they represent validated internal state.
- Add `tests/unit/test_filtering_sections.py` with small synthetic dataframes.
- If report filtering is shared, preserve `ReportModeConfig.default_filters`
  behavior exactly and cover it with regression tests.

## TDD sequence

### Red: add failing pure-function tests

Write tests first for:

- `data.mapping` winning when that column exists;
- fallback to a string `QC.mapping` when the data mapping is absent;
- selection of the first available entry from an ordered `QC.mapping` list;
- a missing filter column disabling the entire preset with an actionable
  warning;
- missing display columns being omitted, in order, with warnings;
- all display columns missing disabling the preset;
- `equals`, `in`, case-insensitive `contains`, lower-only range, upper-only
  range, and inclusive two-sided range;
- multiple filters combining with AND;
- every operator excluding missing values;
- numeric range coercing numeric-looking values and excluding nonnumeric or
  missing values;
- an empty result remaining a valid dataframe;
- the input dataframe remaining exactly unchanged; and
- declaration order surviving resolution.

Use dataframe equality checks, including index and dtypes where practical, to
prove the input was not mutated.

### Green: build resolution and filtering helpers

- Resolve one field by trying an available `data.mapping` column first, then
  the configured `QC.mapping` candidate or candidates in order.
- Resolve every preset once against the complete loaded dataframe.
- Represent runtime availability explicitly, including warnings and the ordered
  display-column list.
- Treat any missing filter column as fail-closed: the preset is unavailable and
  no partially filtered dataset is returned.
- Omit missing display columns but make the preset unavailable if none remain.
- Apply conditions to a copy of the input dataframe.
- Use case-insensitive, missing-safe string matching for `contains`.
- Use inclusive comparisons for range and a numeric series derived without
  mutating the source column.
- Keep this layer independent of buttons, query parameters, and session state.

### Refactor

- Share mask-building logic across preset conditions without weakening the
  explicit operator types from FS-01.
- If adapting report-mode filters to shared predicates, add regression tests
  before refactoring and keep report mode separate from preset state.
- Keep warnings as data returned to the dashboard so the pure layer is easy to
  test.

## Acceptance criteria

- Every operator and AND composition matches the source plan.
- Resolution follows `data.mapping`, then ordered `QC.mapping` fallback.
- Missing filter columns can never broaden the visible dataset.
- Partially available display columns retain their configured relative order.
- Applying a preset never mutates `QCDashboard.data` or the passed dataframe.
- No Streamlit stub is needed by this test module.

## Verification

```bash
pixi run pytest tests/unit/test_filtering_sections.py
pixi run pytest tests/unit/test_dashboard.py -k report_filter
pixi run ruff check src/uQCme/core tests/unit/test_filtering_sections.py
pixi run ruff format --check src/uQCme/core tests/unit/test_filtering_sections.py
git diff --check
```

## Layman's explanation

The mapping uses friendly descriptions, but the table uses real column names.
This task connects the two and then performs the actual filtering. It is kept
separate from the web page so its rules can be tested like a calculator: give it
a small table and a rule, and verify the exact rows returned. If a required
column is missing, the view is switched off instead of silently showing too
much data.
