# FS-04: Compose preset and manual sidebar filters

Status: **Not started**

## Dependency and blocker contract

- **Blocked by:** FS-02 and FS-03.
- **Can start when:** A caller can resolve the active preset, apply it through a
  pure helper, and invoke tested activation/reset transitions.
- **May run in parallel with:** FS-05.
- **Unlocks:** FS-06 and FS-07, together with FS-05.

## Outcome

The sidebar renders one built-in Streamlit button per usable FilteringSection
before the manual filters. The dashboard derives `filtered_data` by applying the
active preset to a copy of `self.data` and then applying the existing manual
filters with AND logic.

## Likely code and test locations

- Refactor `render_sidebar_filters()` and its filter-widget helpers in
  `src/uQCme/app/main.py`.
- Add or extend interaction tests in `tests/unit/test_dashboard.py`.
- Reuse the pure filter engine from FS-02 and state transitions from FS-03.

## TDD sequence

### Red: add failing sidebar and pipeline tests

Write tests first for:

- buttons appearing in YAML order before existing manual filter controls;
- the active button being visibly identifiable using supported Streamlit button
  options, without custom CSS;
- unavailable presets being disabled with one actionable warning;
- button activation delegating to the FS-03 state transition;
- preset filtering occurring before manual filtering;
- preset and manual filters combining with AND;
- overlapping manual filters having been reset on activation while unrelated
  filters remain effective;
- users adding a further manual filter while a preset is active;
- manual widget choices being derived from complete `self.data`, even when the
  preset result does not contain those choices;
- a preserved manual choice producing a valid empty result without widget
  failure or automatic reset;
- `self.data` staying unchanged across repeated renders;
- all tabs receiving the final `filtered_data` through the existing `run()`
  plumbing;
- no buttons, warnings, or filtering changes when `FilteringSections` is
  absent; and
- report mode retaining its separate current behavior.

Update the Streamlit stub only as required to observe button order, disabled
state, selected widget values, and reruns.

### Green: integrate the two filtering layers

- Resolve available presets against the complete loaded dataframe once per
  rerun and render buttons in declaration order.
- Keep the existing sidebar summary at the top, then render the preset controls
  before the manual filter header and widgets.
- Disable unsafe presets rather than allowing activation.
- Start with `baseline = self.data.copy()`.
- If a valid preset is active, pass the baseline through the FS-02 filter
  helper. Otherwise retain the baseline.
- Apply manual widgets afterward to produce the final `filtered_data`.
- Refactor widget helpers so their domain/default bounds come from `self.data`
  while their masks are applied to the progressively filtered dataframe.
- Keep zero-row results valid and continue rendering summary metrics and tabs.
- Do not change `self.data`, QC dataframes, or report-mode defaults.

### Refactor

- Separate “data used to build widget choices” from “data being filtered” in
  function names and parameters.
- Remove duplicated preset resolution or warnings if FS-05 also needs the
  active runtime object; keep one stable per-rerun source of truth.
- Keep the main method readable by extracting preset-control rendering and
  manual-filter application when useful.

## Acceptance criteria

- Buttons, labels, and order are entirely mapping-driven.
- Only one preset is active, and switching uses the FS-03 semantics.
- The final pipeline is preset first, manual filters second.
- Existing tabs continue to consume all columns of the row-filtered dataframe.
- Manual widget domains remain stable from the full dataset while a preset is
  active.
- The no-FilteringSections and report-mode paths remain regression-tested.

## Verification

```bash
pixi run pytest tests/unit/test_dashboard.py -k "sidebar or preset or filtering_section or report_filter"
pixi run ruff check src/uQCme/app/main.py tests/unit/test_dashboard.py
pixi run ruff format --check src/uQCme/app/main.py tests/unit/test_dashboard.py
git diff --check
```

## Layman's explanation

This task wires the new view buttons into the existing filter sidebar. Choosing
a view first narrows the full table according to its saved rules. The familiar
manual filters are then applied on top, so they act like extra conditions. The
manual controls still learn their available choices from the full dataset,
which prevents saved choices from disappearing just because the selected view
currently has no matching rows.
