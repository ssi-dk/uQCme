import importlib

import pytest

from tests.support.dashboard import StreamlitStub


# Patch only this module for this test; never replace installed packages globally.
@pytest.fixture
def streamlit_stub(monkeypatch):
    stub = StreamlitStub()
    dashboard = importlib.import_module("uQCme.app.main")
    monkeypatch.setattr(dashboard, "st", stub)
    return stub
