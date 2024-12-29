"""
Copyright (c) 2024 Matt Miguel. All rights reserved.

llm_toolbelt: Define python functions and easily embed them into LLM function/tool usage.
"""

from __future__ import annotations

from ._version import version as __version__

__all__ = ["__version__"]

from .core import Toolbelt, APIOMORPHIC_AVAILABLE
