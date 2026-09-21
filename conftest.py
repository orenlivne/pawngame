"""Root conftest so the test suite runs from the CLI (`pytest` at repo root).

The project keeps importable code under ``src`` (IDE "sources root"), so add it to
``sys.path`` here rather than requiring an editable install.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
