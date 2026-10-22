from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import pandas as pd
from pydantic import RootModel, StrictStr, ValidationError

from .exceptions import ConfigError


# Validate the canonical-name -> accepted-input-names configuration boundary.
class SpeciesAliasesConfig(RootModel[dict[StrictStr, list[StrictStr]]]):
    pass


# Missing values have no comparable species name; other values stay explicit.
def normalize_species(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return text.casefold() if text else None


# One validated lookup serves rule selection, value comparison and UI support.
@dataclass(frozen=True)
class SpeciesResolver:
    canonical_names: Mapping[str, str]

    @classmethod
    def from_mapping(
        cls, mapping: Mapping[str, Any], *, rule_species: Iterable[str] = ()
    ) -> "SpeciesResolver":
        raw_aliases = mapping.get("SpeciesAliases")
        try:
            config = SpeciesAliasesConfig.model_validate(
                {} if raw_aliases is None else raw_aliases
            )
        except ValidationError as error:
            raise ConfigError(f"Invalid SpeciesAliases: {error}") from error

        rule_names: dict[str, str] = {}
        for value in rule_species:
            normalized = normalize_species(value)
            if normalized is not None and normalized != "all":
                rule_names.setdefault(normalized, str(value).strip())
        names = dict(rule_names)
        for canonical, aliases in config.root.items():
            canonical_key = normalize_species(canonical)
            for alias in aliases:
                alias_key = normalize_species(alias)
                if canonical_key not in rule_names and alias_key in rule_names:
                    raise ConfigError(
                        f"SpeciesAliases must use the QC rule name "
                        f"'{rule_names[alias_key]}' as its key; move '{canonical}' "
                        "into that name's alias list."
                    )
            canonical = rule_names.get(canonical_key, canonical.strip())
            for value in [canonical, *aliases]:
                normalized = normalize_species(value)
                if normalized is None or normalized == "all":
                    raise ConfigError(
                        "SpeciesAliases names must be nonempty and cannot be 'all'."
                    )
                previous = names.get(normalized)
                if previous is not None and previous != canonical:
                    raise ConfigError(
                        f"Ambiguous SpeciesAliases name '{value}': "
                        f"'{previous}' and '{canonical}'."
                    )
                names[normalized] = canonical
        return cls(names)

    def resolve(self, value: Any) -> str | None:
        normalized = normalize_species(value)
        if normalized is None:
            return None
        return self.canonical_names.get(normalized, str(value).strip())

    def matches(self, first: Any, second: Any) -> bool:
        first_name = normalize_species(self.resolve(first))
        second_name = normalize_species(self.resolve(second))
        return first_name is not None and first_name == second_name


# Explicit report roles allow arbitrary source columns; legacy data uses species.
def species_data_field(mapping: Mapping[str, Any]) -> str:
    for section in mapping.get("Sections", {}).values():
        if not isinstance(section, dict):
            continue
        for definition in section.values():
            if not isinstance(definition, dict):
                continue
            if definition.get("report", {}).get("species"):
                column = definition.get("data", {}).get("mapping")
                if isinstance(column, str) and column:
                    return column
    return "species"
