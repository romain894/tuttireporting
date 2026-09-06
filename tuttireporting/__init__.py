"""Build editable LaTeX projects from declarative report definitions and run data."""
from ._version import __version__
from .builder import build_project

__all__ = ["build_project"]
