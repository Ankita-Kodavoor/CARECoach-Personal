"""
Database management for the CARE-adaptive-curriculum application.
"""

import os
import traceback
from . import config
from .logger import get_logger
from . import db_postgres

logger = get_logger(__name__)

def get_db_connection():
    """Returns a connection to the PostgreSQL database"""
    try:
        return db_postgres.get_connection()
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        traceback.print_exc()
        raise

# External DB connection is not used in the Railway deployment
# def get_external_db_connection():
#     """This function is not used in the Railway deployment"""
#     logger.warning("External DB connections are not supported in the Railway deployment")
#     return None

def initialize_database():
    """Creates database tables if they don't exist"""
    try:
        # Import PostgreSQL schema initializer
        from .postgres_schema import initialize_postgres_schema
        
        # Initialize PostgreSQL schema
        success = initialize_postgres_schema()
        if success:
            logger.info("PostgreSQL database initialized successfully")
        else:
            logger.error("PostgreSQL database initialization failed")
        
        return success
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        traceback.print_exc()
        return False

def initialize_practice_session(user_id, chat_code):
    """
    Initialize a practice session for a user/chat_code combination.
    Returns the practice session ID.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if a session already exists for this user/chat code
        cursor.execute("""
            SELECT practicesession_id FROM practice_session
            WHERE user_id = %s AND chat_code = %s
        """, (user_id, chat_code))
        
        session = cursor.fetchone()
        if session:
            session_id = session[0]
            logger.info(f"Practice session already exists for user {user_id} and chat {chat_code}")
            
            # Return the existing session ID
            conn.close()
            return session_id
        
        # If no session exists, try to create it
        # First, compute target skill
        target_skill = None
        try:
            from . import simplest_ranking
            ranked_skills = simplest_ranking.compute_final_rank(user_id, chat_code)
            if ranked_skills:
                target_skill = ranked_skills[0][0]  # take top ranked skill
        except Exception as e:
            logger.error(f"Error computing target skill: {str(e)}")
            target_skill = "Questions"  # fallback to default
        
        # Create default practice session
        import datetime
        import json
        
        # Default values for all required fields
        default_state_history = json.dumps([
            {"state": "stage_A", "timestamp": datetime.datetime.now().isoformat(), "transition": "continue"}
        ])
        
        default_context = json.dumps({
            "User interaction": "Helper: Hello, how are you today?",
            "Feedback": ["Try to use more open-ended questions"],
            "Feedback area to focus": [target_skill or "Questions"]
        })
        
        # Insert a new practice session
        cursor.execute("""
            INSERT INTO practice_session (
                user_id, 
                chat_code, 
                target_skill, 
                current_state,
                utterance_alternative,
                utterance_feedback,
                target_subskill,
                utterance_rewind,
                user_context,
                state_history
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, 
            chat_code, 
            target_skill or "Questions", 
            "stage_A",
            "How have you been feeling lately?",  # Default alternative
            "Practice using more open-ended questions",  # Default feedback
            "Using more open-ended questions/probes",  # Default subskill
            "Helper: How are you today?",  # Default rewind
            default_context,
            default_state_history
        ))
        
        conn.commit()
        
        # Get the new session ID
        cursor.execute("""
            SELECT practicesession_id FROM practice_session
            WHERE user_id = %s AND chat_code = %s
        """, (user_id, chat_code))
        
        session = cursor.fetchone()
        session_id = session[0] if session else None
        
        # Add a default subskill entry
        if session_id:
            try:
                cursor.execute("""
                    INSERT INTO subskill_map 
                    (practicesession_id, utterance_id, utterance, feedback, subskill, completed)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    session_id, 
                    1,  # Default utterance ID 
                    "How are you feeling today?",  # Default utterance 
                    "Practice using more open-ended questions",  # Default feedback
                    "Using more open-ended questions/probes",  # Default subskill
                    False
                ))
                conn.commit()
            except Exception as e:
                logger.error(f"Error creating default subskill: {str(e)}")
        
        conn.close()
        logger.info(f"Created new practice session {session_id} for user {user_id} and chat {chat_code}")
        return session_id
        
    except Exception as e:
        logger.error(f"Error initializing practice session: {str(e)}")
        return None