import pandas as pd
import pytest

from uQCme.core.exceptions import ConfigError
from uQCme.core.species import SpeciesResolver


@pytest.fixture
def species_resolver():
    return SpeciesResolver.from_mapping(
        {"SpeciesAliases": {"Klebsiella pneumoniae": ["K. pneumoniae", "KP"]}}
    )


@pytest.mark.parametrize("value", ["Klebsiella pneumoniae", " K. PNEUMONIAE ", "kp"])
def test_aliases_resolve_to_the_configured_rule_name(species_resolver, value):
    assert species_resolver.resolve(value) == "Klebsiella pneumoniae"
    assert species_resolver.matches(value, "Klebsiella pneumoniae")


@pytest.mark.parametrize("value", [None, pd.NA, float("nan"), "", "   "])
def test_missing_species_never_match(species_resolver, value):
    assert species_resolver.resolve(value) is None
    assert not species_resolver.matches(value, value)


def test_unconfigured_species_are_not_guessed(species_resolver):
    assert species_resolver.resolve("Klebsiella") == "Klebsiella"
    assert not species_resolver.matches("Klebsiella", "Klebsiella pneumoniae")


@pytest.mark.parametrize(
    "aliases",
    [
        {"Species A": ["shared"], "Species B": [" SHARED "]},
        {"Species A": ["Species B"], "Species B": []},
        {"Species A": "A"},
        {"": ["A"]},
        {"Species A": [""]},
        {"all": ["A"]},
        {"Species A": ["all"]},
    ],
)
def test_invalid_or_ambiguous_aliases_fail_at_the_configuration_boundary(aliases):
    with pytest.raises(ConfigError, match="SpeciesAliases"):
        SpeciesResolver.from_mapping({"SpeciesAliases": aliases})


@pytest.mark.parametrize("mapping", [{}, {"SpeciesAliases": None}])
def test_omitted_aliases_keep_literal_species_matching(mapping):
    resolver = SpeciesResolver.from_mapping(mapping)
    assert resolver.matches("Species A", " species a ")
    assert not resolver.matches("A", "Species A")


def test_reversed_legacy_alias_entries_have_an_actionable_error():
    with pytest.raises(ConfigError, match="QC rule name"):
        SpeciesResolver.from_mapping(
            {"SpeciesAliases": {"K. pneumoniae": ["Klebsiella pneumoniae"]}},
            rule_species=["Klebsiella pneumoniae"],
        )


def test_rule_spelling_is_canonical_even_when_config_or_input_case_differs():
    resolver = SpeciesResolver.from_mapping(
        {"SpeciesAliases": {"klebsiella PNEUMONIAE": ["KP"]}},
        rule_species=["Klebsiella pneumoniae"],
    )
    assert resolver.resolve("kp") == "Klebsiella pneumoniae"
    assert resolver.resolve("KLEBSIELLA PNEUMONIAE") == "Klebsiella pneumoniae"
