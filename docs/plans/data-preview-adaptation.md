# Data Preview Adaptation Plan

## Status

**Complete — 2026-08-18**

- This plan is scoped to the public `uQCme` application repository.
- The first implementation slice moved Section Visibility above the Data
  Preview table.
- Regression coverage verifies the intended heading, selector, tip, and table
  render order while preserving report mode and existing table behavior.
- The full test suite passed with 183 tests, and dashboard smoke tests passed
  with 3 tests.
- Ruff was unavailable in the active environment and was not installed or
  added to the lock file.
- Future Data Preview improvements should preserve the same user-centered
  principle: users should be able to shape the table easily before reviewing
  its contents.

## Layperson's summary

Data Preview should adapt to the user's needs. The controls that decide which
sections of data are shown should appear before the table, so users can choose
the information that fits their task before they start reviewing rows.

The table's own column controls remain available for finer-grained changes.

## Product principle: user-shaped Data Preview

Data Preview has two levels of visibility:

- **Section Visibility** chooses larger groups of related columns.
- **Table column visibility** allows individual columns to be shown or hidden.

Section Visibility is the higher-level choice, so it should appear above the
table. This makes the interaction easier to understand:

1. Choose the sections relevant to the task.
2. Review the resulting table.
3. Optionally hide or show individual columns within those sections.

The controls should remain compact and close to the table they affect.

## Handoff context

This plan applies to the public `uQCme` repository.

Relevant implementation locations are:

- `src/uQCme/app/main.py`
  - `QCDashboard.render_data_tab()`
  - `_render_section_visibility_control()`
- `tests/unit/test_dashboard.py`
  - Data Preview rendering and section visibility regression tests.
- Existing Data Preview selection and column behavior.

Before this plan was implemented, the Section Visibility controls rendered
after the table. The implementation now renders them before the table while
preserving the existing visibility state and table behavior.

## Approved product decisions

- Render the **Section Visibility** heading, selector, and explanatory tip
  above the Data Preview table.
- Keep the existing compact Streamlit pills/multi-select control.
- Preserve the existing `data_preview_visible_sections` session-state key.
- Keep the table's individual column visibility controls unchanged.
- Keep the CSV download after the table.
- Keep row selection and configured sample API actions unchanged.
- Do not render Section Visibility controls in report mode.
- Do not introduce custom JavaScript or a new UI component for this change.

## Implementation plan

### 1. Lock the intended render order with a regression test

Update the existing Data Preview rendering test so it verifies that the normal
interactive Data tab emits these events in order:

```text
Section Visibility heading
Visible sections selector
Explanatory tip
Data Preview table
```

Rename the test to reflect the intended behavior:

```text
test_data_tab_renders_section_visibility_above_table
```

Retain the existing tests covering:

- report mode without Section Visibility controls;
- selected sections changing the displayed columns;
- an empty section selection producing an empty table.

### 2. Move Section Visibility before table rendering

In `QCDashboard.render_data_tab()`:

- Continue resolving visible sections from the existing mapping and session
  state.
- Continue calculating `ordered_columns`, `active_sections`, and
  `display_data` in the existing way.
- Render Section Visibility immediately after `display_data` is prepared and
  immediately before the report-mode or interactive table branch.
- Leave the table rendering implementation unchanged.

This changes presentation order only. It does not change how visible sections
are selected or how columns are calculated.

### 3. Preserve dependent behavior

Verify that moving the controls does not change:

- Data Preview column order;
- row selection behavior;
- selected sample lookup;
- sample API actions;
- full-column CSV export;
- column information;
- report mode;
- reset behavior for section visibility state.

The section selector must continue to control the same table on the next
Streamlit rerun.

### 4. Validate and review

Run the focused dashboard tests first. Then run the full repository test suite
and dashboard smoke tests.

Review the final diff to confirm that the change is limited to the Data Preview
render order and its regression coverage.

## Tests and acceptance criteria

The change is accepted when:

- Section Visibility appears above the Data Preview table.
- The heading, selector, and explanatory tip appear together.
- Selecting or deselecting sections still changes the displayed columns.
- The table's individual column controls remain available.
- Report mode remains table-only.
- Row selection and sample API actions continue to use the same data.
- CSV export behavior remains unchanged.
- The full test suite passes.
- Dashboard smoke tests pass.
- No private deployment or server configuration is changed.

## Verification

Run from the repository root:

```bash
pixi run pytest tests/unit/test_dashboard.py -k \
  "data_tab or data_preview or selected_sample or sample_api"

pixi run test
pixi run test-dashboard-smoke
ruff check .
ruff format .
git diff --check
```

If Ruff is unavailable in the active environment, report that reproducibility
gap rather than installing it or changing the lock file.

## Out of scope

- Redesigning the Section Visibility control.
- Changing section names, labels, or mapping semantics.
- Changing table-level column visibility controls.
- Changing report mode.
- Changing row selection, API actions, or CSV export.
- Adding pagination, custom JavaScript, or a new table component.
- Changes to deployment repositories or server environments.
