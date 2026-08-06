import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

import pandas as pd

from uQCme.app.styling import (
    MISSING_SPECIES,
    MISSING_SPECIES_LABEL,
    MISSING_SPECIES_TABLE_LABEL,
    SUPPORTED_SPECIES,
    UNSUPPORTED_SPECIES,
    SpeciesSupportStyling,
)
from uQCme.core.config import UIStylingConfig


def _styling() -> SpeciesSupportStyling:
    return SpeciesSupportStyling(
        UIStylingConfig(
            unsupported_species_color_light="#123456",
            unsupported_species_color_dark="#654321",
            missing_species_color="#ABCDEF",
            missing_species_opacity=0.25,
        ),
        supported_species={"Escherichia coli"},
    )


def test_species_support_matches_trimmed_names_without_regard_to_case():
    styling = _styling()

    assert styling.state_for("  ESCHERICHIA COLI ") == SUPPORTED_SPECIES
    assert styling.table_label_for("  Escherichia coli ") == "Escherichia coli"
    assert styling.cell_style_for("Escherichia coli") == ""


def test_species_support_distinguishes_unsupported_and_missing_values():
    styling = _styling()

    assert styling.state_for("Salmonella enterica") == UNSUPPORTED_SPECIES
    unsupported_style = styling.cell_style_for("Salmonella enterica")
    assert "light-dark(#123456, #654321)" in unsupported_style
    assert "font-weight" not in unsupported_style
    assert "background-color" not in unsupported_style

    for missing_value in (None, pd.NA, math.nan, "", "   "):
        assert styling.state_for(missing_value) == MISSING_SPECIES
        assert styling.chart_label_for(missing_value) == MISSING_SPECIES_LABEL
        assert styling.table_label_for(missing_value) == MISSING_SPECIES_TABLE_LABEL


def test_missing_species_style_uses_translucent_neutral_background():
    styling = _styling()

    assert styling.cell_style_for(None) == (
        "background-color: rgba(171, 205, 239, 0.25);"
    )
