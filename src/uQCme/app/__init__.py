"""Streamlit app module for uQCme.

Note: This module requires the 'app' or 'all' extras to be installed:
    pip install uqcme[app]
"""

from uQCme.app.main import main, QCDashboard

__all__ = ["main", "QCDashboard"]
