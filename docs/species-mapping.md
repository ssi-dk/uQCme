# Species mapping and QC caveats

`mapping.yaml` owns both source-column mappings and accepted species names.
The QC engine and dashboard use the same species resolver.

## Canonical names and aliases

Use the species name from the QC rules as the key. Its list contains accepted
input names:

```yaml
SpeciesAliases:
  Klebsiella pneumoniae:
    - K. pneumoniae
  Escherichia coli:
    - E. coli
```

Names are compared after trimming whitespace and ignoring case. No abbreviation,
substring or biological equivalence is inferred. A missing or blank name never
matches another name. An alias cannot belong to two canonical names, and `all`
is reserved for rules that apply to every species. Invalid or ambiguous mappings
raise a configuration error.

The resolver uses the canonical name when selecting species-specific rules and
evaluating rules mapped to the species source column. For example,
`K. pneumoniae` selects the `Klebsiella pneumoniae` rules and satisfies a species
value check matching `^Klebsiella pneumoniae`. Results retain the original input
value. Other metric values and rule thresholds are unchanged.

The dashboard uses that same resolution for provided/detected comparisons and
rule-support styling. A configured alias indicates support only if the canonical
species has explicit QC rules; `all` rules do not establish species support.

### Migrating earlier mappings

Earlier dashboard-only examples put the alias on the left:

```yaml
# Earlier format: replace this entry.
SpeciesAliases:
  K. pneumoniae:
    - Klebsiella pneumoniae
```

Invert those entries to the canonical-key format above before updating. When
loaded rules reveal an inverted entry, validation reports the rule name that
must become its key. Do not maintain a second alias list under `app`.

## Mapping a different source column

The default species column is `species`. To use another name, mark that mapped
field with `report.species: true`. Its QC mappings identify the rule fields that
read the same value:

```yaml
Sections:
  Basic:
    Provided species:
      data:
        mapping: organism
      QC:
        mapping: [speciesName, genusName, Marker lineage]
      report:
        species: true
```

The engine selects species rules from `organism` in this example. Mark only one
source field as the provided species. Detected results remain separate fields.

## Missing metrics are caveats

Missing metrics preserve the existing QC outcome and action logic:

- An absent column skips its applicable rules.
- A null or blank value in a present column retains the existing failed-rule
  behaviour.
- Available rules still determine the configured pass/fail or warning result.

Two additional result columns expose the caveat for each sample:

| Column | Contents |
| --- | --- |
| `skipped_rules` | Comma-separated applicable rule IDs skipped because their source column is absent. |
| `missing_qc_fields` | Comma-separated source columns whose applicable rules encountered absent or missing values. |

These fields are empty when no applicable QC input is missing. Unrelated species
rules do not add caveats. Global warning output remains available.

Sample Details displays a warning alongside the sample's QC outcome when
`missing_qc_fields` is populated. The example Standard table also includes this
column. A pass with caveats means that available checks passed; it does not
establish that every requested metric was available. Data supplied by an external
API must include these fields to carry its per-sample caveats into the dashboard.

## Local examples and optional UI configuration

The repository's default config uses synthetic file input. Generate results
before opening the dashboard:

```bash
uqcme --config config.yaml
uqcme-dashboard --config config.yaml
```

`config.api.test.yaml` is an explicit API-integration example. The default file
workflow does not require an API process or token.

Column presets are optional. If omitted or empty, the basic table uses its
native controls. Providing presets enables the preset buttons and grouped
customizer. `sample_details.index_columns` is also optional: its default index
uses the mapped sample ID, species, QC outcome and QC action when present. An explicit list
selects source columns in that order. Other dashboard defaults remain active.
