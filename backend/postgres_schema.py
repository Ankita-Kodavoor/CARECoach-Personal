"""
PostgreSQL schema initialization for the CARE-adaptive-curriculum application.
"""

import sys
import traceback
from . import db_postgres

def initialize_postgres_schema():
    """Creates all required tables in PostgreSQL database"""
    print("Initializing PostgreSQL schema...", file=sys.stderr)
    
    try:
        conn = db_postgres.get_connection()
        cursor = conn.cursor()
        
        # Create all tables with PostgreSQL syntax
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS practice_session (
                practicesession_id SERIAL PRIMARY KEY,
                user_id TEXT,
                chat_code TEXT,
                target_skill TEXT,
                target_utterance_id INTEGER,
                utterance_feedback TEXT,
                utterance_alternative TEXT,
                user_context TEXT,
                target_subskill TEXT,
                utterance_rewind TEXT,
                current_state TEXT,
                state_history TEXT,
                UNIQUE(user_id, chat_code)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS freeform_dialogue (
                practicesession_id INTEGER,
                practice_chat_id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                utterance TEXT NOT NULL,
                role TEXT NOT NULL,
                state TEXT,
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (practicesession_id) REFERENCES practice_session (practicesession_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subskill_map (
                practicesession_id INTEGER,
                utterance_id INTEGER NOT NULL,
                utterance TEXT NOT NULL,
                feedback TEXT,
                subskill TEXT,
                completed BOOLEAN,
                FOREIGN KEY (practicesession_id) REFERENCES practice_session (practicesession_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                practicesession_id INTEGER,
                practice_chat_id INTEGER,
                score INTEGER,
                utterance TEXT,
                state TEXT,
                time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (practice_chat_id) REFERENCES freeform_dialogue (practice_chat_id) ON DELETE CASCADE
            )
        """)
        
        # For demo purposes, you might want to add the extracted* tables too
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_conversation (
                id SERIAL PRIMARY KEY,
                chat_code TEXT,
                role TEXT,
                utterance TEXT,
                time TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_feedback (
                utterance_id INTEGER,
                chat_code TEXT,
                feedback TEXT,
                perfect TEXT,
                goodareas TEXT,
                badareas TEXT,
                alternative TEXT,
                time TEXT,
                FOREIGN KEY (utterance_id) REFERENCES extracted_conversation (id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("PostgreSQL schema initialization completed successfully", file=sys.stderr)
        return True
    except Exception as e:
        print(f"Error initializing PostgreSQL schema: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False
