# Sample Details Direct Replacement Plan

## Status

**Complete — 2026-08-06**

- The dropdown was replaced with the all-sample navigation table and linked
  detail sections described below.
- Shared natural sample ordering is applied after filtering to interactive and
  report views without mutating the source dataframe.
- Passed rules were removed from Sample Details while failed rules and the
  underlying result columns were preserved.
- A follow-up rendering defect was fixed by emitting the navigation table as
  contiguous, left-aligned HTML instead of Markdown-indented HTML.
- The navigation table uses theme-safe translucent borders and header styling.
- The navigation table is config-forward: displayed fields, labels, and order
  are derived from report metadata in the mapping configuration.
- The result follows a Streamlit-first hybrid design. HTML is limited to the
  navigation table and anchor targets required for same-page navigation;
  Streamlit renders the surrounding dashboard and sample details.
- Regression coverage verifies renderable HTML, table contents, links, unique
  anchors, escaping, configured columns, ordering, filtering, and existing
  warning behavior.
- Local validation passed: 110 tests, 3 dashboard smoke tests, Python
  compilation, and `git diff --check`. Ruff was unavailable in the active
  environment and was not installed or added to the lock file.
- The user confirmed that the repaired navigation table works as intended.

**Detected-species follow-up complete — 2026-08-18**

- Basic Information now keeps the existing provided `species` row and adds a
  compact **detected species** row directly beneath it.
- The provided/category value is resolved through the existing
  `_get_species_field()` mapping behavior. The detected value is resolved from
  the configured detected field, currently `rMLST_match`.
- Direct matches are green after trimming whitespace and case-folding.
  Explicitly configured biological aliases are also accepted; no fuzzy,
  substring, abbreviation, or automatic alias matching is used.
- Missing, blank, unknown, mismatched, or unmapped values are red. Missing
  detected values display as an em dash (`—`).
- The detected-species comparison is rendered only in Sample Details. It is
  not added to the navigation table, Data Preview, exports, QC rule fields,
  or API contracts.
- The implementation remains Streamlit-first. It uses the existing
  `st.write()` and `st.markdown()` patterns, with only the minimal escaped
  inline span required to color the detected value. No new CSS, JavaScript,
  component, configuration flag, or schema field was introduced for the UI.
- A duplicate mapped-column rendering defect was fixed so two mapping labels
  that refer to the same dataframe column cannot create an ambiguous pandas
  selection in Data Preview.
- Current validation passed: 196 tests, 3 dashboard smoke tests, and
  `git diff --check`. Ruff remains unavailable in the active environment and
  was not installed or added to the lock file.

## Layperson's summary

Replace the sample dropdown with a table of all filtered samples. Clicking a
sample name will jump to that sample's details farther down the page. Samples
will be sorted naturally by name, failed rules will remain visible, and passed
rules will be removed from this view.

Basic Information also shows the provided/category species and the detected
program result underneath it. The detected value is visibly green when it
matches directly or through an explicitly configured alias, and red when it
does not match or is unavailable.

## Architecture decision: Streamlit-first hybrid

The Sample Details page deliberately uses a small hybrid of native Streamlit
and HTML. This is an exception for one navigation capability, not a general
direction for the dashboard.

A fully native Streamlit table can display and select rows, but selection
causes a Streamlit rerun and does not provide reliable same-page anchor links.
That model naturally leads to showing one selected sample's details at a time.
The agreed design instead keeps every filtered sample detail section on the
page and lets users jump directly to any section without replacing the others.

To preserve that behavior, HTML is used only for:

- the compact navigation table, whose sample links target detail sections; and
- the small, invisible anchor targets for the table and sample sections.

Streamlit remains responsible for tabs, headings, filters, warnings, detail
layout, columns, metrics, rule results, and interactive controls. The **Back to
sample index** links and visual separators use ordinary Markdown or Streamlit
rendering rather than custom HTML. No JavaScript component is used.

Future changes should keep this boundary narrow. Custom HTML should be added
only when required behavior has no practical Streamlit equivalent, and should
remain local, escaped, theme-safe, and covered by regression tests. Where
Streamlit or ordinary Markdown can express the UI, they remain the preferred
implementation.

The detected-species indicator follows the same principle. Streamlit owns the
row, label, layout, and lifecycle. The only HTML is the minimal inline span
needed to color the data-derived value. This keeps the feature compatible with
the existing dashboard without introducing a custom component or a second
styling system.

### Config-forward navigation columns

The navigation table is driven by the same mapping configuration that
describes report fields, avoiding a second hard-coded column list in dashboard
code. A field opts into the index through report metadata:

```yaml
Name:
  data:
    mapping: sample_name
  report:
    id: true
    sample_details_index: true
    sample_details_order: 1
    label: Sample
```

- `sample_details_index: true` includes the field in the navigation table.
- `sample_details_order` controls its left-to-right position.
- `label` optionally supplies its displayed heading.
- `id: true` identifies the sample field used for links and anchor targets.

The bundled default mapping produces **Sample**, **Species**, **QC outcome**,
and **QC action** in that order. A configuration can add, remove, reorder, or
relabel navigation columns without changing Python code. Mappings without the
new metadata retain the legacy four-column layout for backward compatibility.

The detected species is intentionally not a navigation column. Navigation
continues to identify samples and summarize the configured report fields;
comparison status belongs in the detail presentation where the provided and
detected values can be read together.

### Detected-species comparison

Sample Details treats `species` as the provided/category species and
`rMLST_match` as the detected program result. The local example mapping makes
that contract explicit:

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

The name **Expected species** is retained as a mapping field for compatibility
with existing configuration terminology, but its value is displayed as the
detected result in Sample Details. It is not promoted into the sample index.

Biological naming differences are kept in the mapping YAML as explicit
provided-to-detected aliases:

```yaml
SpeciesAliases:
  E. coli:
    - Escherichia coli
  Salmonella:
    - Salmonella enterica
  S. sonnei:
    - Shigella sonnei
  Yersinia:
    - Yersinia enterocolitica
```

The comparison normalizes only by trimming whitespace and case-folding. It
first checks exact normalized equality, then checks the configured aliases for
the normalized provided value. Missing or blank values never match. New
biological equivalences require an explicit mapping review rather than a
Python-code change or an automatic inference.

## Handoff context for a new chat

This plan applies to the public `uQCme` repository. uQCme is a Streamlit
application for reviewing quality-control results derived from microbial
whole-genome sequencing data.

Before implementation, read the repository `AGENTS.md` and inspect the current
working tree. At the time this plan was written, the tree already contained
user-owned modifications, including changes to:

- `src/uQCme/app/main.py`
- `tests/unit/test_dashboard.py`
- configuration, plotting, documentation, and styling files

Preserve those changes and do not assume that `HEAD` represents the current
dashboard behavior. The workspace context and linked wiki documents referenced
by `AGENTS.md` were not present in this checkout when the plan was prepared.
Stay within this repository and do not connect to any server.

### Pre-implementation state

- `QCDashboard.run()` passes the filtered dataframe to every interactive tab.
- `QCDashboard.render_sample_details_tab()` currently creates a Streamlit
  dropdown, selects the first matching row, and renders only that sample.
- The sample identity is obtained from the mapping field marked
  `report.id: true`. In the default mapping, this maps to `sample_name`.
- The existing sample detail layout contains Basic Information, Quality
  Metrics, QC action/outcome, failed rules, and passed rules.
- Report/PDF mode uses a separate table-only renderer and does not render the
  Sample Details tab.
- The existing sample-details unit coverage is in
  `tests/unit/test_dashboard.py`, including the quality-metric rendering test.

## Approved product decisions

- Implement the **direct replacement** design; do not add a display-mode
  configuration option or retain the dropdown.
- Render all samples that remain after the existing sidebar/report filters.
- Add a compact navigation table above the detail sections.
- The bundled defaults display **Sample**, **Species**, **QC outcome**, and
  **QC action**, but the columns, labels, and order come from mapping report
  metadata.
- Keep the implementation Streamlit-first. Restrict custom HTML to the table
  and anchors that are required for in-page navigation.
- Keep the detected-species indicator Streamlit-first. Use native Streamlit
  rendering wherever possible and restrict HTML to the minimal inline color
  span required for compact text styling.
- Make the sample name itself the anchor link. Do not add a separate
  **Details** column because it duplicates the link's purpose.
- Add a **Back to sample index** link to each sample section.
- Remove passed rules from Sample Details only. Do not remove the underlying
  `passed_rules` data, processing, Data Preview column, or report/export column.
- Sort samples by the canonical `sample_name` field using stable, natural,
  case-insensitive ascending order. For example, `Sample-2` must appear before
  `Sample-10`.
- Apply this order to all dashboard views after filtering, including the
  table-only report/PDF view. Do not mutate `self.data` or change filter
  semantics.
- If `sample_name` is unavailable, preserve the incoming order. Put missing
  sample names after populated names when the column exists.
- Render all filtered samples without pagination or a sample-count cap.
- Keep `species` as the provided/category value and use the configured
  detected field, currently `rMLST_match`, only for the Sample Details
  comparison.
- Color a matching detected value green and every non-match red, including
  missing, blank, unknown, and unmapped values. Display missing detected
  values as `—`.
- Escape every data-derived detected value before it reaches the minimal
  inline HTML span.
- Do not add a detected-species column to the navigation table.

## Implementation plan

### 1. Add shared sample ordering

- Add a small dashboard helper that returns a sorted copy of a dataframe.
- Build the natural-sort key with the Python standard library rather than
  adding a dependency: split names into numeric and non-numeric chunks,
  compare text chunks using `casefold()`, and compare numeric chunks as
  integers.
- Make the sort stable so duplicate/equivalent names retain their input order.
- Apply the helper immediately after `render_sidebar_filters()` returns and
  before dispatching to report mode or the interactive tabs. This makes Data
  Preview, plots, Sample Details, actions, and report output receive the same
  row order.

### 2. Refactor one-sample rendering

- Extract the existing single-sample presentation from
  `render_sample_details_tab()` into a helper that accepts one row plus the
  resolved field names and metric context.
- Preserve the existing Basic Information, quality-metric formatting, QC
  outcome/action coloring, and failed-rule behavior.
- Remove the passed-rules column and all passed-rules output from this helper.
  Let the failed-rules area use the available width cleanly.
- Follow the repository convention for new function/class documentation:
  comments above definitions rather than new docstrings.

### 3. Replace the dropdown with anchor navigation

- Keep the current validation for an empty filtered dataframe and a missing
  configured ID field.
- Build one unique anchor per filtered row. Derive a readable slug from the
  configured sample identity and add a deterministic occurrence suffix when
  names are duplicated. Never use unsanitized sample text as HTML attributes.
- Render a top-of-view anchor followed by a compact static navigation table.
  Use HTML/Markdown rather than `st.dataframe`, because genuine in-page
  fragment links are required.
- Derive included fields, labels, and ordering from mapping report metadata.
  Use an em dash for unavailable values and retain the legacy four-column
  layout for mappings that have not adopted the metadata.
- HTML-escape every data-derived label and cell value before rendering with
  `unsafe_allow_html=True`.
- Loop over the naturally sorted filtered rows. Before each extracted detail
  section, render its anchor target; after it, render a link back to the sample
  index and a visual separator.
- Keep custom CSS minimal and local to the navigation table, consistent with
  the repository preference for native Streamlit UI.
- Use native Streamlit or ordinary Markdown for all surrounding page elements,
  including back links and separators.

### 4. Add the detected-species indicator

- Reuse `_get_species_field()` for the provided/category species so QC and
  Sample Details continue to agree about the source field.
- Resolve the detected field from the mapping metadata, with `rMLST_match` as
  the current default when no more specific detected-species label is present.
- Pass the resolved detected field into `_render_single_sample_details()`.
- Render the row immediately below the provided `species` row using the
  existing Streamlit `st.markdown()` pattern already used for QC action
  coloring.
- Keep the label in the normal theme text and apply color only to the escaped
  detected value. Use green for direct or explicit-alias matches and red for
  all other states.
- Leave the three-column Basic Information, Quality Metrics, and Failed Rules
  layout unchanged. Keep failed-rule-only display, metric formatting, QC
  action styling, anchors, and Back to sample index links unchanged.
- Avoid new Streamlit components, JavaScript, CSS, flags, or API/schema
  changes. The existing Streamlit dashboard remains the primary renderer.

## Tests and acceptance criteria

Update dashboard unit tests to cover:

- Natural, case-insensitive ordering: `Sample-1`, `sample-2`, `Sample-10`.
- Stable handling of duplicate names and missing values.
- Preservation of source order when `sample_name` is absent.
- Global use of the sorted filtered dataframe by interactive and report paths.
- Navigation table columns, labels, and order follow mapping report metadata.
- Legacy mappings without navigation metadata retain the four default columns.
- No separate Details column and no dropdown in Sample Details.
- Each sample-name link targets the correct detail section.
- Duplicate or unusual sample names produce valid, unique anchors.
- HTML-sensitive sample values are escaped rather than interpreted as markup.
- The navigation fragment starts at column zero, is passed with HTML enabled,
  and is not interpreted as an indented Markdown code block.
- Every filtered sample renders exactly once and filtered-out samples do not
  render.
- Passed rules do not appear in Sample Details; failed rules and existing
  quality metrics still do.
- Existing empty-data and missing-ID warnings continue to work.
- The provided species remains the existing `species` row and the detected
  species row appears directly beneath it for every filtered sample.
- Direct normalized matches render green.
- Configured aliases render green for all approved equivalence examples.
- Mismatches, missing detected values, unknown categories, and unmapped values
  render red, with missing values shown as `—`.
- The detected field is resolved from mapping metadata and is not added to the
  navigation table.
- Reused mapping columns do not create duplicate pandas dataframe columns or
  break Data Preview rendering.

After implementation, run the repository-prescribed checks without installing
or changing dependencies incidentally:

```text
ruff check .
ruff format .
pixi run test
pixi run test-dashboard-smoke
```

If Ruff is unavailable in the active environment, report that reproducibility
gap rather than installing it or altering the lock file. Inspect the resulting
diff to ensure only intended files changed and all pre-existing user changes
remain intact.

## Out of scope

- A configurable choice between dropdown and full-table modes
- Pagination, lazy loading, or a maximum number of detail sections
- Changes to QC evaluation, filtering rules, API actions, or source data
- Removing `passed_rules` outside the Sample Details presentation
- Changes to server or deployment configuration
