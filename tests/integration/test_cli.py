import sys
from pathlib import Path

import pandas as pd
import yaml
from streamlit.testing.v1 import AppTest

from uQCme.cli.main import main


def test_default_synthetic_workflow_creates_output_and_renders_offline(processor_factory, monkeypatch):
    processor = processor_factory("local_example")
    directory = Path(processor.qc_config.output.results).parent
    config_path = directory / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    for key in ("results", "warnings"):
        config["qc"]["output"][key] = str(directory / "generated" / key / (key + ".tsv"))
    config["app"]["input"]["data"] = {"file": config["qc"]["output"]["results"]}
    config["app"]["input"]["warnings"] = config["qc"]["output"]["warnings"]
    config_path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(sys, "argv", ["uqcme", "--config", str(config_path)])
    main()
    results = pd.read_csv(config["qc"]["output"]["results"], sep="\t")
    assert len(results) == 19
    assert "FAIL_GENERAL" in results.set_index("sample_name").loc["example_fail_assembly", "qc_outcome"]
    script = "from uQCme.app.main import QCDashboard\nQCDashboard(" + repr(str(config_path)) + ").run()"
    app = AppTest.from_string(script).run(timeout=15)
    assert not app.exception
    assert any("QC caveat" in warning.value for warning in app.warning)
