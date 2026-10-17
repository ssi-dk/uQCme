from pathlib import Path

import yaml

from uQCme.core.engine import QCProcessor


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


# Each run owns its outputs and log; inputs are immutable, public fixtures.
def make_processor(schema: str, output_dir: Path) -> QCProcessor:
    fixture = "config_example.yaml" if schema == "legacy" else "config_new_schema.yaml"
    config_path = (
        REPOSITORY_ROOT / "config.yaml"
        if schema == "local_example"
        else REPOSITORY_ROOT / "tests/fixtures" / fixture
    )
    config = yaml.safe_load(config_path.read_text())
    output_dir.mkdir(parents=True, exist_ok=True)
    for section_name in ("qc", "app"):
        inputs = config[section_name]["input"]
        for field in ("mapping", "qc_rules", "qc_tests", "warnings"):
            if field in inputs:
                inputs[field] = str(REPOSITORY_ROOT / inputs[field])
        data = inputs["data"]
        if isinstance(data, str):
            inputs["data"] = str(REPOSITORY_ROOT / data)
        elif data.get("file"):
            data["file"] = str(REPOSITORY_ROOT / data["file"])
    config["qc"]["output"] = {
        "results": str(output_dir / "results.tsv"),
        "warnings": str(output_dir / "warnings.tsv"),
    }
    if schema == "local_example":
        config["app"]["input"]["data"] = {"file": config["qc"]["output"]["results"]}
        config["app"]["input"]["warnings"] = config["qc"]["output"]["warnings"]
    config["log"]["file"] = str(output_dir / "qc.log")
    config_path = output_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    return QCProcessor(str(config_path))
