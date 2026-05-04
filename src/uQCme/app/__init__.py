"""Streamlit app module for uQCme.

Note: This module requires the 'app' or 'all' extras to be installed:
    pip install uqcme[app]
"""

__all__ = ["main", "QCDashboard"]


def __getattr__(name):
    """Load dashboard objects lazily so app extras stay optional."""
    if name in __all__:
        from uQCme.app.main import QCDashboard, main

        return {"main": main, "QCDashboard": QCDashboard}[name]
    raise AttributeError(name)
