# FS-07: Complete integration and regression verification

Status: **Complete**

## Dependency and blocker contract

- **Blocked by:** FS-04, FS-05, and FS-06. FS-01 through FS-03 are indirect hard
  blockers through those tasks.
- **Can start when:** Every earlier task's targeted tests pass and its changelog
  checkbox is complete.
- **Unlocks:** Feature handoff.
- **No partial handoff:** A failure here reopens the task that owns the broken
  behavior; it is not waived as a final-test issue.

## Outcome

High-level tests prove that the separate configuration, filtering, URL state,
sidebar, Data Preview, and selection changes work as one feature. The complete
repository quality gate passes, and the changelog accurately records delivery.

## TDD sequence

### Red: add end-to-end regression scenarios first

Before writing any final integration glue, add dashboard-level tests covering
complete user journeys:

1. Start without a preset, set unrelated and overlapping manual filters,
   activate a preset, and verify replacement/preservation plus final AND
   filtering.
2. Start a fresh dashboard session from a shared preset URL and verify rows,
   exact Data Preview columns, hidden section controls, and unchanged
   `self.data`.
3. Switch presets, create a valid empty result with an additional manual
   filter, then clear the view and verify URL, widgets, selection, editor state,
   and normal section defaults.
4. Load mappings with an unknown URL key, a missing filter column, some missing
   display columns, no available display columns, and no FilteringSections.
5. Select a row and trigger the existing action plumbing while the ID and action
   value fields are absent from the displayed preset columns.
6. Verify Overview, Quality Metrics, and Sample Details receive the same
   preset-and-manual row result with all filtered-data columns available.

Run these tests and confirm any failure identifies a real integration gap. Make
the smallest fix in the owning module, then rerun that earlier task's focused
tests as well as the high-level scenario.

### Green and refactor

- Wire any remaining per-rerun active preset object through the dashboard so
  the sidebar and Data Preview cannot disagree.
- Deduplicate warnings and ensure they appear in an actionable place once per
  rerun.
- Remove temporary compatibility paths or duplicate helpers introduced while
  FS-04 and FS-05 were developed in parallel.
- Review changed public functions and classes for repository comment style,
  typing, and `None` comparisons.
- Do not expand scope into report-mode redesign, CLI behavior, deployment, or
  private automation.

## Final acceptance checklist

- [x] Valid config parsing and YAML order are covered.
- [x] All malformed operator/value combinations are rejected.
- [x] Field fallback and every operator are covered.
- [x] Multiple filters use AND and preserve the source dataframe.
- [x] Buttons, URL activation, switching, refresh, and unknown keys are covered.
- [x] Overlapping and unrelated manual filter state behaves as specified.
- [x] Full reset removes all owned state and preserves unrelated URL state.
- [x] Preset columns are exact and ordered, and section controls are hidden.
- [x] Missing-column safety behavior is covered.
- [x] Selection and API actions work without a displayed ID column.
- [x] Absence of FilteringSections retains existing behavior.
- [x] Examples and README match the tested public interface.
- [x] No private or deployment details are present.

## Required verification order

Run the repository commands from the repository root:

```bash
pixi run ruff check .
pixi run ruff format .
pixi run test
pixi run test-dashboard-smoke
git diff --check
```

If formatting changes files, rerun the affected targeted tests before the full
suite. Inspect `git diff` and `git status --short` to ensure only intended public
repository files changed. Convert the FilteringSections entry in
`CHANGELOG.md` from an in-progress checklist to a concise delivered feature
description, or mark every checkbox complete according to the repository's
preferred changelog style.

## Layman's explanation

The earlier tasks build individual parts, like the rule checker, buttons, and
table. This final task tests them as a person would use them from beginning to
end. It verifies that a shared link restores the right view, extra filters still
work, reset truly cleans up, hidden columns stay hidden, and sample actions
still receive the information they need. Only after the whole repository's
checks pass is the feature ready to hand over.
