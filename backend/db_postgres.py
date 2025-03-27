"""
PostgreSQL database connector for the CARE-adaptive-curriculum application.
"""

import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
import traceback

def get_connection():
    """Returns a connection to the PostgreSQL database"""
    try:
        # Railway automatically sets DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
            
        conn = psycopg2.connect(database_url, cursor_factory=DictCursor)
        # Set timezone for consistent timestamp behavior
        with conn.cursor() as cursor:
            cursor.execute("SET timezone TO 'UTC';")
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        raise
