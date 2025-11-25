"""uQCme - Microbial Quality Control Dashboard"""

try:
    from ._version import version as __version__
except ImportError:
    try:
        from importlib.metadata import version, PackageNotFoundError
        __version__ = version("uQCme")
    except (ImportError, PackageNotFoundError):
        __version__ = "unknown"
