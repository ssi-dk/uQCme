# FS-03: Manage URL selection and reset state

Status: **Complete**

## Dependency and blocker contract

- **Blocked by:** FS-01 and FS-02.
- **Can start when:** Presets have stable typed and resolved runtime
  representations, including availability status.
- **Unlocks:** FS-04 and FS-05, which may then proceed in parallel.
- **Must preserve:** Existing query parameters such as `debug`, `report_mode`,
  and forwarded API parameters.

## Outcome

Small dashboard helpers determine the active preset from
`?filtering_section=<key>`, activate or switch a preset, clear the complete view
state, and remove only overlapping manual filters on activation.

## Likely code and test locations

- Add focused state helpers in `src/uQCme/app/main.py`, or a small app-layer
  module if that keeps Streamlit access isolated.
- Extend the Streamlit test double in `tests/unit/test_dashboard.py` so tests can
  choose button results and record reruns without treating them as unexpected.
- Keep URL handling on Streamlit's built-in `st.query_params`; do not add custom
  JavaScript.

## State ownership to make explicit

- URL: `filtering_section` only.
- Manual filter widgets: `range_<column>`, `filter_<column>`, and
  `search_<column>`.
- Sample-name search: `search_sample_name` when the configured ID column is one
  of the preset-controlled columns.
- Selection: `selected_samples`.
- Data Preview: `data_preview_table` and
  `data_preview_visible_sections`.
- Existing reset coordination: `filters_reset`, if still needed after the
  refactor.

## TDD sequence

### Red: add failing state-transition tests

Write tests first for:

- resolving a known URL key as the active preset;
- preserving names containing spaces and other URL-encoded characters;
- a fresh session with the same URL restoring the preset, simulating a hard
  refresh;
- an unknown URL key warning once and returning the normal unpresetted view;
- a known but runtime-disabled preset warning and returning the normal view;
- activating a preset setting/replacing only `filtering_section` and rerunning;
- switching from one preset to another;
- activation clearing every widget-key form for preset-controlled columns;
- activation preserving unrelated manual filter keys and selections;
- clearing the view removing the preset, all manual filter keys, sample
  selection, editor state, and section-visibility state;
- clearing the view preserving unrelated URL parameters and unrelated session
  state; and
- reset restoring normal section defaults on the next rerun.

### Green: implement explicit state transitions

- Read the active key from `st.query_params` on every rerun.
- Match only exact FilteringSection keys; never guess or normalize a different
  key.
- Centralize manual-widget key generation so activation and rendering cannot
  drift apart.
- On activation, delete only state keys belonging to columns controlled by the
  selected preset, set the URL parameter, and rerun.
- On clear, remove the preset parameter without clearing the entire query
  string, delete all feature-owned manual and table state, clear selections,
  and rerun.
- Return warnings as explicit outcomes or render them once from a single caller
  to avoid duplicate messages across tabs.

### Refactor

- Keep URL parsing, state-key calculation, activation, and full reset as
  separately testable helpers.
- Remove ad hoc reset branches from widget functions only if equivalent tests
  cover their replacement.
- Ensure no helper mutates dataframe content.

## Acceptance criteria

- Shared links and hard refreshes restore a valid preset.
- Unknown or unavailable URL presets fail safely to the existing view.
- Switching presets replaces the active key and clears overlapping manual
  widget values.
- Unrelated manual filters survive activation.
- “Clear View & Filters” removes all feature-owned view state but preserves
  unrelated query parameters.
- Tests use built-in Streamlit-compatible state behavior only.

## Verification

```bash
pixi run pytest tests/unit/test_dashboard.py -k "filtering_section or clear_view or preset_state"
pixi run ruff check src/uQCme/app/main.py tests/unit/test_dashboard.py
pixi run ruff format --check src/uQCme/app/main.py tests/unit/test_dashboard.py
git diff --check
```

## Layman's explanation

The chosen view is stored in the page address, much like a bookmark. This task
teaches the app how to read that bookmark, replace it when another button is
pressed, and remove it during a full reset. It also carefully clears only
manual filters that would fight with the newly chosen view, while leaving the
user's unrelated choices and unrelated parts of the URL alone.
