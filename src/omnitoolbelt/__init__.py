"""
Copyright (c) 2024 Matt Miguel. All rights reserved.

omnitoolbelt: Define python functions and easily embed them into LLM function/tool usage or discord bot commands.
"""

from __future__ import annotations

from ._version import version as __version__

__all__ = ["__version__",'Toolbelt']

from .toolbelt import Toolbelt, APIOMORPHIC_AVAILABLE

