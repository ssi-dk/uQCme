from typing import Any, Iterable, Mapping, Optional

from uQCme.core.config import UIStylingConfig
from uQCme.core.species import SpeciesResolver, normalize_species


MISSING_SPECIES_LABEL = "Missing species"
MISSING_SPECIES_TABLE_LABEL = "—"
SUPPORTED_SPECIES = "supported"
UNSUPPORTED_SPECIES = "unsupported"
MISSING_SPECIES = "missing"


# Resolve species values to rule-support states and subtle display styling.
class SpeciesSupportStyling:
    # Build a normalized supported set once so all surfaces classify values
    # using the same trimming and case-folding rules.
    def __init__(
        self,
        config: UIStylingConfig,
        supported_species: Iterable[str],
        species_aliases: Optional[Mapping[str, Iterable[str]]] = None,
    ):
        self.config = config
        supported_species = tuple(supported_species)
        self.resolver = SpeciesResolver.from_mapping(
            {"SpeciesAliases": species_aliases or {}}, rule_species=supported_species
        )
        self._supported_species = {
            normalize_species(self.resolver.resolve(value))
            for value in supported_species
            if normalize_species(value) not in (None, "all")
        }

    def is_missing(self, value: Any) -> bool:
        return normalize_species(value) is None

    # Classify a value as missing, supported by rules, or unsupported.
    def state_for(self, value: Any) -> str:
        if self.is_missing(value):
            return MISSING_SPECIES

        normalized_value = normalize_species(self.resolver.resolve(value))
        if normalized_value in self._supported_species:
            return SUPPORTED_SPECIES
        return UNSUPPORTED_SPECIES

    # Replace blank and null chart labels with a visible category name.
    def chart_label_for(self, value: Any) -> str:
        if self.is_missing(value):
            return MISSING_SPECIES_LABEL
        return str(value).strip()

    # Replace blank and null table values with a compact visible marker.
    def table_label_for(self, value: Any) -> str:
        if self.is_missing(value):
            return MISSING_SPECIES_TABLE_LABEL
        return str(value).strip()

    # Return a subtle cell style for missing or unsupported values.
    def cell_style_for(self, value: Any) -> str:
        state = self.state_for(value)
        if state == SUPPORTED_SPECIES:
            return ""
        if state == UNSUPPORTED_SPECIES:
            return (
                "color-scheme: light dark; color: light-dark("
                f"{self.config.unsupported_species_color_light}, "
                f"{self.config.unsupported_species_color_dark});"
            )

        red, green, blue = _hex_to_rgb(self.config.missing_species_color)
        opacity = self.config.missing_species_opacity
        return f"background-color: rgba({red}, {green}, {blue}, {opacity});"


# Convert validated six-digit hex colors for translucent missing-cell styling.
def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    return (
        int(color[1:3], 16),
        int(color[3:5], 16),
        int(color[5:7], 16),
    )
