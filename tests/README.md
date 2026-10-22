# uQCme tests

Run the maintained environment from the repository root:

```bash
pixi run test                 # essential: routine functional baseline
pixi run test-conditional     # remaining regressions after relevant changes
pixi run test-all             # complete local suite before release / broad changes
pixi run test-packaging
pixi run test-dashboard-smoke
```

With that environment already active, `python -m pytest` is equivalent to the
complete suite, not the default essential task. Pytest configures the source import path centrally.

## Responsibilities

| Location | Coverage |
| --- | --- |
| `unit/test_species.py` | Canonical names, aliases, missing names, ambiguous configuration and migration errors. |
| `unit/test_qc_processor.py`, `unit/test_qc_caveats.py` | Operators, rule/field mapping, QC conditions and per-sample missing-metric caveats. |
| `unit/test_dashboard_*.py` | API handling, tables, sample details and filters with a fresh, scoped Streamlit double. |
| `unit/test_config.py`, `unit/test_styling.py`, `unit/test_plot.py` | Configuration boundaries, styling decisions and plot semantics. |
| `integration/test_qc_outcomes.py` | Fresh synthetic processing, legacy outcome compatibility, new-schema failures, aliases and output writing. |
| `integration/test_example_fixture.py` | Fixture identity/schema, deterministic generation and comparison of the maintained example with freshly computed results. |
| `integration/test_dashboard_runtime.py` | Real Streamlit defaults, optional preset/customizer interactions, navigation links, descriptions and QC caveats. |
| `integration/test_cli.py` | Offline CLI-to-dashboard workflow, including fresh output directories and the default example presets. |
| `test_python_standalone_packaging.py`, `unit/test_dashboard_smoke.py` | Packaging contracts and smoke-helper parser/command construction. |
| `support/` | Shared test doubles and isolated processor configuration helpers. |

## Isolation and fixtures

- Inputs contain synthetic, public-safe examples only. Never fetch operational
  data to run these tests.
- HTTP requests are blocked by an autouse fixture. API tests explicitly mock
  their transport; unexpected requests fail the test.
- Processing helpers resolve input paths explicitly and put results, warnings
  and logs under pytest's temporary directory.
- Integration tests inspect `processor.results` from the run they just performed.
  The checked-in legacy TSV is an expected baseline, not the actual result.
- Dashboard doubles patch only the dashboard module for the requesting test.
  Installed Streamlit/plot modules are not replaced in `sys.modules`.
- Plot tests choose their theme explicitly so real Streamlit theme registration
  cannot change their expected palette through test order.

The maintained new-schema processed fixture is checked against fresh processing.
Regenerate it deliberately when the public example changes; tests must not
rewrite expected results to make themselves pass. The raw fixture generator is
`fixtures/generate_new_schema_fixture.py` and uses the public source data plus
`fixtures/new_schema_columns.txt`.

The `dashboard_smoke` tests check helper configuration and command construction.
They do not establish that a dashboard process started, that PDF export works,
or that any remote deployment is healthy.


## Choosing the level

`python tests/run.py essential|conditional|all --list` previews the selection.
The essential baseline checks fresh QC outcomes, species rules/aliases, bearer
request handling and safe identity. Run it during normal development; add the
changed area's tests when the diff touches another behaviour. Conditional is the
remaining, disjoint local suite. `all` is their union; it does not build bundles,
start Docker or deploy anything. Do not run essential + conditional + all for the
same revision: choose essential + the affected tests, or one complete run.

Packaging changes additionally require `test-packaging`; source/UI/transport
changes need their corresponding dashboard/CLI integration tests. The separate
owning deployment flow rehearses real systemd/NFS and production-shaped synthetic
APIs. Keep a regression only when it protects a distinct behaviour or a documented
failure; do not duplicate assertions just to raise test counts. Use elapsed time
and risk, not test count, when deciding what runs frequently.
