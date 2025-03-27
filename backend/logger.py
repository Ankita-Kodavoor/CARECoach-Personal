"""
Centralized logging configuration for the CARE-adaptive-curriculum application.
"""

import logging
import sys
from . import config

# Configure root logger
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

def get_logger(name):
    """Returns a configured logger instance with the given name"""
    logger = logging.getLogger(name)
    return logger