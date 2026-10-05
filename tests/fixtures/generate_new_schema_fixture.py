#!/usr/bin/env python3
"""Generate the public synthetic fixture for the new export schema."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


_CATEGORY_SPECIES = {
    "example_pass_ecoli": "E. coli",
    "example_pass_general_fail_species_kp": "K. pneumoniae",
    "example_fail_read_qc": "Salmonella",
}

_RMLST_MISMATCHES = {
    "example_warn_review": "Cronobacter sakazakii",
    "example_fail_assembly": "Cronobacter sakazakii",
}

_RMLST_MISSING = {"test_fail_adapter"}

_SOURCE_TO_NEW = {
    "Quast_Total_Length": "bin_length_at_1x",
    "Quast_GC_Pct": "GC",
    "Average_Coverage": "coverage_x",
    "Quast_N50": "N50",
    "Quast_Contigs": "bin_contigs_at_1x",
    "fastp_Before_Filtering_Total_Reads": "filtered_reads_num",
    "fastp_Before_Filtering_Read1_Mean_Length": "mean_read_length_bp",
    "fastp_Before_Filtering_Read2_Mean_Length": "mean_read_length_bp",
    "fastp_After_Filtering_Total_Reads": "filtered_reads_num",
    "fastp_After_Filtering_Read1_Mean_Length": "mean_read_length_bp",
    "fastp_After_Filtering_Read2_Mean_Length": "mean_read_length_bp",
    "fastp_Duplication_Rate": "duplication_rate",
}


# Read the canonical column order without reading any real export rows.
def _read_columns(path: Path) -> list[str]:
    columns = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    columns = [column for column in columns if column]
    if len(columns) != len(set(columns)):
        raise ValueError("New-schema column manifest contains duplicate columns")
    if "Select" in columns:
        raise ValueError("The dashboard-only Select column must not be in the fixture")
    return columns


# Read the old synthetic rows and validate the join key and lab groups.
def _read_source_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        reader = csv.DictReader(source_file, delimiter="\t")
        if reader.fieldnames is None:
            raise ValueError("Source fixture has no header")
        required = {"sample_name", "species", "lab_group"}
        missing = required.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Source fixture is missing columns: {sorted(missing)}")
        rows = list(reader)

    sample_names = [row["sample_name"] for row in rows]
    if len(sample_names) != len(set(sample_names)):
        raise ValueError("Source fixture contains duplicate sample_name values")
    if any(not row["lab_group"].strip() for row in rows):
        raise ValueError("Source fixture contains a blank lab_group value")
    return rows


# Build one new-schema row while preserving the old synthetic metrics.
def _build_row(source_row: dict[str, str], columns: list[str]) -> dict[str, str]:
    sample_name = source_row["sample_name"]
    species = _CATEGORY_SPECIES.get(sample_name, source_row["species"])
    if sample_name in _RMLST_MISSING:
        rmlst_match = ""
    elif sample_name in _RMLST_MISMATCHES:
        rmlst_match = _RMLST_MISMATCHES[sample_name]
    else:
        rmlst_match = source_row["species"]

    row = {column: "" for column in columns}
    for column, source_column in _SOURCE_TO_NEW.items():
        row[column] = source_row.get(source_column, "")

    row["sample_name"] = sample_name
    row["species"] = species
    row["rMLST_match"] = rmlst_match
    row["rMLST_support"] = "" if not rmlst_match else "100"
    row["lab_group"] = source_row["lab_group"]
    row["SeqSampleID"] = sample_name
    row["RunID"] = "synthetic-example-run"
    row["MLST_Species"] = species
    row["Bracken_Species"] = rmlst_match
    row["Bracken_Species1"] = rmlst_match
    row["Bracken_Species_Pct"] = "99.0" if rmlst_match else ""
    row["Bracken_Species1_Pct"] = "98.0" if rmlst_match else ""
    row["Bracken_Unclassified_Pct"] = "1.0" if rmlst_match else ""
    return row


# Generate a deterministic tab-separated new-schema fixture.
def generate_fixture(source: Path, columns_file: Path, output: Path) -> None:
    columns = _read_columns(columns_file)
    source_rows = _read_source_rows(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = [_build_row(source_row, columns) for source_row in source_rows]

    with output.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(
            output_file,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


# Parse command-line paths for reproducible local fixture generation.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--columns", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate_fixture(args.source, args.columns, args.output)


if __name__ == "__main__":
    main()
