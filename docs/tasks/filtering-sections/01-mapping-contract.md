# FS-01: Define and validate the mapping contract

Status: **Complete**

## Dependency and blocker contract

- **Blocked by:** Nothing. This is the first implementation task.
- **Can start when:** The developer has read `FilteringSections_plan.md`,
  `PLAN.md`, and the repository instructions.
- **Unlocks:** FS-02.
- **Does not unlock:** UI work directly. Runtime resolution behavior belongs to
  FS-02.

## Outcome

The dashboard can load an optional, typed `FilteringSections` object from
`mapping.yaml`. Invalid operator/value combinations fail at the YAML boundary
with an actionable configuration error. Existing mappings without this key
continue to load unchanged.

## Likely code and test locations

- Add a focused module such as `src/uQCme/core/mapping.py` for mapping-boundary
  models and parsing. Avoid forcing the existing arbitrary `Sections` structure
  into a new schema as part of this feature.
- Integrate parsing with mapping loading in `src/uQCme/app/main.py`.
- Add focused tests such as
  `tests/unit/test_filtering_sections_config.py`.
- Keep `self.mapping` available to existing code unless a broader migration is
  explicitly approved.

## TDD sequence

### Red: add failing contract tests

Write tests before production code for:

- a valid mapping containing multiple FilteringSections;
- preservation of YAML declaration order for presets, columns, and filters;
- an absent `FilteringSections` key producing an empty typed collection;
- `data.mapping` references;
- `QC.mapping` as a string and as an ordered list;
- rejection of an unsupported operator;
- rejection of `in` with an empty or missing `values` list;
- rejection of `equals` or `contains` without `value`;
- rejection of `range` without `min` or `max`;
- acceptance of lower-only, upper-only, and two-sided ranges; and
- conversion of Pydantic validation failures into a useful dashboard
  configuration error rather than an unhandled exception.

Run the new test file and confirm the failures point to the missing parser and
models.

### Green: implement the smallest boundary model

- Model a reusable mapping-style field reference with optional `data.mapping`
  and `QC.mapping` fields.
- Model the four explicit condition shapes: `equals`, `in`, `contains`, and
  `range`. Prefer a discriminated union or equivalent validation that makes
  invalid value combinations impossible after parsing.
- Model each FilteringSection as an ordered mapping of display columns plus an
  ordered mapping of filters.
- Parse only the new top-level key immediately after YAML loading. Do not
  duplicate the whole legacy mapping schema.
- Store the parsed collection on the dashboard, or return it from a dedicated
  loader with an explicit type.
- Preserve native mapping order; do not sort names or fields.
- Wrap validation failures in the repository's existing configuration-error
  path with enough location detail to identify the preset and condition.

### Refactor

- Remove duplicated field-reference declarations between column and filter
  models.
- Keep validators small and operator-specific.
- Add comments above new classes and functions in accordance with repository
  style; do not add implementation docstrings.

## Acceptance criteria

- Valid examples parse into typed boundary objects in declaration order.
- Invalid configurations are rejected before any preset button is rendered.
- No downstream code needs to inspect raw operator dictionaries.
- Loading a mapping without `FilteringSections` produces no new warning or UI.
- Existing `Sections`, `QC_overrides`, and other top-level mapping content remain
  available to current consumers.
- The relevant `CHANGELOG.md` checkbox and description are updated before this
  task is marked complete.

## Verification

```bash
pixi run pytest tests/unit/test_filtering_sections_config.py
pixi run ruff check src/uQCme/core src/uQCme/app/main.py tests/unit/test_filtering_sections_config.py
pixi run ruff format --check src/uQCme/core src/uQCme/app/main.py tests/unit/test_filtering_sections_config.py
git diff --check
```

## Layman's explanation

The YAML file is user input, so this task adds a careful receptionist at the
door. It checks that every named view has a list of columns and understandable
rules, such as “equals local” or “between 10 and 100.” If a rule is incomplete,
the app explains the configuration problem early instead of failing later or
showing the wrong samples. Older mapping files simply pass through without any
new behavior.
