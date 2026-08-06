# FS-05: Lock Data Preview columns and preserve row selection

Status: **Complete**

## Dependency and blocker contract

- **Blocked by:** FS-02 and FS-03.
- **Can start when:** The active preset and its ordered, available display
  columns can be obtained without reading raw YAML.
- **May run in parallel with:** FS-04.
- **Unlocks:** FS-06 and FS-07, together with FS-04.

## Outcome

While a preset is active, Data Preview receives only the preset's ordered
display columns and does not render Section Visibility controls. Row selection
and configured sample API actions continue to use the complete row-filtered
dataframe even when its ID or action columns are not displayed.

## Likely code and test locations

- Refactor `render_data_tab()`, `_render_styled_dataframe()`, and selection
  helpers in `src/uQCme/app/main.py`.
- Extend `tests/unit/test_dashboard.py` with table rendering, selection, and API
  action regression cases.
- Reuse FS-02 warnings for omitted or unavailable display columns rather than
  resolving them differently in the table layer.

## TDD sequence

### Red: add failing Data Preview tests

Write tests first for:

- exact preset column order in the dataframe supplied to `st.data_editor`;
- columns not configured by the preset never being supplied to the table;
- Section Visibility pills, heading, and state being bypassed while active;
- built-in table controls still being allowed to hide supplied columns;
- normal section visibility behavior remaining unchanged without a preset;
- missing display columns being omitted with warnings in FS-02 order;
- a preset with no available display columns never reaching this renderer;
- selection checkboxes working when the configured ID column is displayed;
- selection checkboxes also working when the ID column is not displayed;
- selected IDs being looked up from full `filtered_data`, not exposed as a
  hidden table column;
- API actions receiving complete selected rows, including configured
  `value_field` data absent from the display columns;
- non-Data tabs continuing to receive all filtered columns; and
- clearing the view restoring normal section defaults and editor state.

The test editor should simulate checking a row while preserving the dataframe
index so selection can be traced back to the full row safely.

### Green: separate display data from selection data

- When a valid preset is active, build `display_data` from only its resolved
  ordered display columns.
- Pass the full row-filtered dataframe separately as the selection source.
- Add the checkbox to the displayed table without adding the configured ID
  column when that ID is not in the preset.
- Resolve checked rows back to the full dataframe by their stable dataframe
  index, then store the configured IDs in `selected_samples`.
- Keep `_get_selected_sample_rows(filtered_data)` and sample API actions based
  on the complete filtered dataframe.
- Do not pass excluded columns to `st.data_editor`; otherwise its built-in
  column controls could reveal them.
- Bypass both the section-selection widget and its explanatory tip while a
  preset owns visibility.
- Retain the existing section path exactly when no preset is active.

### Refactor

- Make function arguments distinguish `display_data` from `selection_source`.
- Centralize index-alignment checks and handle an unexpected edited index
  safely rather than selecting the wrong sample.
- Avoid custom CSS or JavaScript; use the existing Streamlit editor and state.

## Acceptance criteria

- The active preset provides an ordered, locked maximum set of Data Preview
  columns.
- The existing visibility UI is neither rendered nor applied during a preset.
- Hidden ID and API value fields remain unavailable to table controls but
  available to row actions through full filtered rows.
- Selection is correct after row filtering, including nonconsecutive indexes.
- All legacy Data Preview behavior remains tested without a preset.

## Verification

```bash
pixi run pytest tests/unit/test_dashboard.py -k "data_tab or data_preview or selected_sample or sample_api"
pixi run ruff check src/uQCme/app/main.py tests/unit/test_dashboard.py
pixi run ruff format --check src/uQCme/app/main.py tests/unit/test_dashboard.py
git diff --check
```

## Layman's explanation

The saved view controls which columns are handed to the preview table, so the
table cannot reveal anything outside that list. The app still keeps the full
filtered row behind the scenes. When a user ticks a row, its table position is
matched back to that full row, allowing sample actions to use the ID and other
required values even when those columns are intentionally not shown.
