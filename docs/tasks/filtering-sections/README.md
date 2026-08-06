# FilteringSections TDD task breakdown

This directory breaks
[`FilteringSections_plan.md`](../../../FilteringSections_plan.md) into
implementation-sized tasks. The source plan remains the product-decision record;
these files define the programming sequence, test boundaries, and handoffs.

## Working agreement

For every task:

1. Confirm every hard blocker listed in the task is complete.
2. Update the task status here and the checklist in `CHANGELOG.md`.
3. Add the task's tests first and run them to see the expected failure.
4. Implement only enough production code to make those tests pass.
5. Refactor while keeping the targeted tests green.
6. Run the task verification commands and update the changelog before marking
   the task complete.

Tests must fail because the requested behavior is absent, not because the test
fixture or Streamlit stub is broken. Each task must preserve `self.data` as the
complete baseline dataframe and use only synthetic, public-safe test data.

## Dependency graph

```text
FS-01 Mapping contract
  -> FS-02 Resolution and filter engine
       -> FS-03 URL and reset state
            -> FS-04 Sidebar filter composition ----+
            -> FS-05 Data Preview and selection ----+-> FS-06 Docs/examples
                                                        -> FS-07 Regression gate
```

FS-04 and FS-05 may be developed in parallel after FS-03. FS-06 is blocked
until both user-interface paths are settled, and FS-07 is the final gate.

## Tasks and blockers

| ID | Task | Status | Hard blockers | Unlocks |
| --- | --- | --- | --- | --- |
| FS-01 | [Mapping contract](01-mapping-contract.md) | Complete | None | FS-02 |
| FS-02 | [Resolution and filter engine](02-resolution-and-filter-engine.md) | Complete | FS-01 | FS-03 |
| FS-03 | [URL and reset state](03-url-and-reset-state.md) | Complete | FS-01, FS-02 | FS-04, FS-05 |
| FS-04 | [Sidebar filter composition](04-sidebar-filter-composition.md) | Complete | FS-02, FS-03 | FS-06, FS-07 |
| FS-05 | [Data Preview and selection](05-data-preview-and-selection.md) | Complete | FS-02, FS-03 | FS-06, FS-07 |
| FS-06 | [Examples and documentation](06-examples-and-documentation.md) | Complete | FS-04, FS-05 | FS-07 |
| FS-07 | [Integration and regression gate](07-integration-and-regression.md) | Not started | FS-04, FS-05, FS-06 | Feature handoff |

## Shared boundaries

- Work stays in this public repository. There is no server, deploy-repository,
  or private-data work.
- `FilteringSections` affects dashboard views only. It must not change the CLI,
  QC calculations, stored result files, or report-mode defaults.
- Use Pydantic models only for untrusted YAML input. Use dataclasses for
  resolved, validated runtime objects.
- Prefer built-in Streamlit buttons, query parameters, session state, warnings,
  and table controls. Do not add custom JavaScript or CSS.
- An absent `FilteringSections` key is a supported configuration and must retain
  today's behavior.

## Definition of complete

The feature is complete only when FS-01 through FS-07 are marked complete, the
acceptance cases from the source plan have automated coverage, all verification
commands pass, and `CHANGELOG.md` describes the delivered behavior rather than
only the work in progress.
