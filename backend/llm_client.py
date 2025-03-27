"""
OpenAI client singleton for the CARE-adaptive-curriculum application.
"""

import os
from openai import OpenAI
from . import config
from .logger import get_logger

logger = get_logger(__name__)

def create_openai_client():
    """Creates and configures an OpenAI API client"""
    
    if not config.OPENAI_API_KEY:
        logger.warning("OpenAI API key is not set. LLM functionality will be disabled.")
        return None
    
    # Clean proxy settings if empty
    if os.environ.get('HTTP_PROXY') == '':
        del os.environ['HTTP_PROXY']
    if os.environ.get('HTTPS_PROXY') == '':
        del os.environ['HTTPS_PROXY']
    
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return None

# Create a singleton instance
openai_client = create_openai_client()