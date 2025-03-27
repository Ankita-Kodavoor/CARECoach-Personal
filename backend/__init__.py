# This file makes the backend directory a Python package
# It can be empty, but we'll add basic package info
"""
CARE Coach backend package
"""

__version__ = "0.1.0"

from . import config
from . import logger
from . import simplest_ranking
from . import freeform
from . import subskill

from . import (
    create_input_database,
    response_scorer,
    subskill_manager,
    websocket_server
)
