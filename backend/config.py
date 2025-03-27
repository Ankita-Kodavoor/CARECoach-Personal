"""
Centralized configuration for the CARE-adaptive-curriculum application.
Loads environment variables from .env file if present and provides
sensible defaults for all configuration settings.
"""

import os
import sys
from dotenv import load_dotenv

# Base directory is the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Load environment variables from .env file
if os.path.exists(ENV_PATH):
    print(f"Loading .env from: {ENV_PATH}")
    load_dotenv(ENV_PATH)
else:
    print(f"No .env file found at: {ENV_PATH}")
    load_dotenv()  # Try default loading as fallback

# Database settings
# Railway automatically sets DATABASE_URL, no need to specify it here
USE_EXTERNAL_DB = False  # Disable external DB for Railway deployment

# OpenAI API settings
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_ORGANIZATION = os.environ.get("OPENAI_ORGANIZATION")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")  # Defaulting to GPT-4o

# Server settings
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

# File paths
PROMPTS_DIR = os.environ.get("PROMPTS_DIR", os.path.join(BASE_DIR, "prompts"))

# Logging configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Feature flags
ENABLE_NEXT_SUBSKILL_AUTO = os.environ.get("ENABLE_NEXT_SUBSKILL_AUTO", "True").lower() in ("true", "1", "t")

def get_prompt_path(filename):
    """Returns the full path to a prompt file"""
    return os.path.join(PROMPTS_DIR, filename)

def validate_config():
    """Validates critical configuration settings and returns issues"""
    issues = []
    
    if not OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY is not set")
    
    if not os.path.exists(PROMPTS_DIR):
        issues.append(f"Prompts directory not found: {PROMPTS_DIR}")
    
    # Check if DATABASE_URL is set in production
    if not os.environ.get('DATABASE_URL') and not DEBUG:
        issues.append("DATABASE_URL environment variable is not set")
    
    return issues

def as_dict():
    """Returns configuration as a dictionary with sensitive values masked"""
    return {
        "BASE_DIR": BASE_DIR,
        "DATABASE_URL": "****" if os.environ.get("DATABASE_URL") else None,
        "USE_EXTERNAL_DB": USE_EXTERNAL_DB,
        "OPENAI_API_KEY": "****" if OPENAI_API_KEY else None,
        "OPENAI_ORGANIZATION": "****" if OPENAI_ORGANIZATION else None,
        "OPENAI_MODEL": OPENAI_MODEL,
        "HOST": HOST,
        "PORT": PORT,
        "ALLOWED_ORIGINS": ALLOWED_ORIGINS,
        "DEBUG": DEBUG,
        "PROMPTS_DIR": PROMPTS_DIR,
        "LOG_LEVEL": LOG_LEVEL,
        "ENABLE_NEXT_SUBSKILL_AUTO": ENABLE_NEXT_SUBSKILL_AUTO
    }

# Print configuration summary to stderr on import if in debug mode
if DEBUG:
    print("Configuration loaded:", file=sys.stderr)
    for key, value in as_dict().items():
        print(f"  {key}: {value}", file=sys.stderr)