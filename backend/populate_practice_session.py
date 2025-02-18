import sqlite3

DB_PATH = "saltcare_personal.db"  # Path to your SQLite database

def get_db_connection():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    return conn

def get_next_practicesession_id(cursor):
    """Finds the next available practicesession_id to avoid duplicates."""
    cursor.execute("SELECT MAX(practicesession_id) FROM practice_session;")
    max_id = cursor.fetchone()[0]
    return (max_id + 1) if max_id else 1  # Start from 1 if table is empty

def insert_dummy_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Define dummy data (excluding practicesession_id)
    dummy_data = [
        ("user_001", "dummy_chat_001", "Empathy", 101, "Understanding others' feelings", 
         "How would you respond if someone shares their struggles?", "User is a student", "Emotional Intelligence"),
        ("user_002", "dummy_chat_002", "Active Listening", 102, "Listening without interrupting", 
         "What is the best way to show active listening?", "User is a teacher", "Communication Skills"),
        ("user_003", "dummy_chat_003", "Confidence", 103, "Speaking clearly and assertively", 
         "What helps in building confidence while speaking?", "User is a public speaker", "Public Speaking"),
    ]

    # Insert data into the practice_session table (avoid duplicate practicesession_id)
    for user_id, chat_code, target_skill, target_utterance_id, utterance_feedback, utterance_alternative, user_context, target_subskill in dummy_data:
        practicesession_id = get_next_practicesession_id(cursor)  # Get next unique ID

        cursor.execute("""
            INSERT OR IGNORE INTO practice_session 
            (practicesession_id, user_id, chat_code, target_skill, target_utterance_id, 
             utterance_feedback, utterance_alternative, user_context, target_subskill) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (practicesession_id, user_id, chat_code, target_skill, target_utterance_id, 
              utterance_feedback, utterance_alternative, user_context, target_subskill))

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    print("✅ Dummy data inserted into practice_session!")

if __name__ == "__main__":
    insert_dummy_data()
