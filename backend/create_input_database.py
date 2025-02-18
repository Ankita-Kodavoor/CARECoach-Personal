import sqlite3
import os
from simplest_ranking import compute_final_rank, find_first_utterance

# Define database paths
SOURCE_DB = os.path.abspath("saltcare.db")  # Read from saltcare.db
DESTINATION_DB = os.path.abspath("test_input_v2.db")  # Write to test_input_v2.db

def connect_db(db_path): 
    """Connect to the specified SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Fetch results as dictionaries
    return conn, conn.cursor()

def create_new_database():
    """Creates a new database to store extracted information."""
    conn, cursor = connect_db(DESTINATION_DB)

    # Create table for conversation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_conversation (
            id INTEGER PRIMARY KEY,
            chat_code TEXT,
            role TEXT,
            utterance TEXT,
            time TEXT
        )
    """)

    # Create table for feedback
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

    # Create table for practice session
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_session (
            practicesession_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            chat_code TEXT,
            target_skill TEXT,
            target_utterance_id INTEGER,
            utterance_feedback TEXT,
            utterance_alternative TEXT,
            user_context TEXT,
            target_subskill TEXT,
            UNIQUE(user_id, chat_code),
            FOREIGN KEY (target_utterance_id) REFERENCES extracted_conversation (id)
        )
    """)

    # Create table for knowledge_bite
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_bite (
            practicesession_id INTEGER,
            chat_code TEXT,
            concept TEXT,
            description TEXT,
            timestamp TEXT,
            helpful BOOLEAN,
            FOREIGN KEY (practicesession_id) REFERENCES practice_session (practicesession_id)
        )
    """)

    conn.commit()
    conn.close()

def extract_knowledge_bite():
    """Extracts knowledge_bite from saltcare.db and inserts into test_input_v2.db."""
    src_conn, src_cursor = connect_db(SOURCE_DB)
    dest_conn, dest_cursor = connect_db(DESTINATION_DB)

    # Extract data from knowledge_bite in saltcare.db
    src_cursor.execute("SELECT chat_code, concept, description, timestamp, helpful FROM knowledge_bite")
    rows = src_cursor.fetchall()

    # Insert into test_input_v2.db
    for row in rows:
        dest_cursor.execute("""
            INSERT INTO knowledge_bite (chat_code, concept, description, timestamp, helpful)
            VALUES (?, ?, ?, ?, ?)
        """, (row["chat_code"], row["concept"], row["description"], row["timestamp"], row["helpful"]))

    dest_conn.commit()
    src_conn.close()
    dest_conn.close()
    print(f"✅ {len(rows)} knowledge bite entries copied from saltcare.db to test_input_v2.db!")

def store_extracted_data(conversation, feedback, user_id, chat_code):
    """Stores extracted data into the new database."""
    conn, cursor = connect_db(DESTINATION_DB)

    for conv in conversation:
        cursor.execute("""
            INSERT OR REPLACE INTO extracted_conversation (id, chat_code, role, utterance, time)
            VALUES (?, ?, ?, ?, ?)
        """, (conv["id"], conv["chat_code"], conv["role"], conv["utterance"], conv["time"]))

    for fb in feedback:
        cursor.execute("""
            INSERT OR REPLACE INTO extracted_feedback (utterance_id, chat_code, feedback, perfect, goodareas, badareas, alternative, time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (fb["utterance_id"], fb["chat_code"], fb["feedback"], fb["perfect"], fb["goodareas"], fb["badareas"], fb["alternative"], fb["time"]))

    conn.commit()
    conn.close()

    # Compute target skill and update practice session
    compute_and_store_target_skill(user_id, chat_code)

def compute_and_store_target_skill(user_id, chat_code):
    """Computes target skill and updates practice_session."""
    conn, cursor = connect_db(DESTINATION_DB)

    ranked_skills = compute_final_rank(user_id, chat_code)
    if ranked_skills:
        target_skill = ranked_skills[0][0]
        cursor.execute("""
            INSERT OR REPLACE INTO practice_session (user_id, chat_code, target_skill)
            VALUES (?, ?, ?)
        """, (user_id, chat_code, target_skill))
        conn.commit()

        first_utterance_id = find_first_utterance(user_id, chat_code, target_skill)
        if first_utterance_id is not None:
            cursor.execute("""
                UPDATE practice_session 
                SET target_utterance_id = ? 
                WHERE user_id = ? AND chat_code = ? AND target_skill = ?
            """, (first_utterance_id, user_id, chat_code, target_skill))
            conn.commit()

    conn.close()

def get_conversation_and_feedback(user_id, chat_code):
    try:
        create_new_database()
        
        conn, cursor = connect_db(SOURCE_DB)

        cursor.execute("""
            SELECT id, user_id, utterance, time
            FROM dialog
            WHERE chat_code = ?
            ORDER BY time ASC
        """, (chat_code,))
        conversation = cursor.fetchall()

        conversation_history = []
        helper_utterance_ids = []

        for row in conversation:
            dialog_id, sender_id, utterance, timestamp = row
            role = "Helper" if sender_id == user_id else "Seeker"
            conversation_history.append({
                "id": dialog_id,
                "chat_code": chat_code,
                "role": role,
                "utterance": utterance,
                "time": timestamp
            })
            if sender_id == user_id:
                helper_utterance_ids.append(dialog_id)

        if helper_utterance_ids:
            format_ids = ",".join("?" * len(helper_utterance_ids))
            cursor.execute(f"""
                SELECT utterance_id, feedback, perfect, goodareas, badareas, alternative, time
                FROM feedback
                WHERE chat_code = ? AND utterance_id IN ({format_ids})
            """, (chat_code, *helper_utterance_ids))
            feedback_data = cursor.fetchall()
        else:
            feedback_data = []

        feedback_list = [{
            "utterance_id": row[0],
            "chat_code": chat_code,
            "feedback": row[1],
            "perfect": row[2],
            "goodareas": row[3],
            "badareas": row[4],
            "alternative": row[5],
            "time": row[6]
        } for row in feedback_data]

        conn.close()
        store_extracted_data(conversation_history, feedback_list, user_id, chat_code)
        extract_knowledge_bite()  # Extract knowledge bite after conversation and feedback

        return {"conversation": conversation_history, "feedback": feedback_list}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    while True:
        user_id = input("Enter user ID (or type 'exit' to quit): ")
        if user_id.lower() == "exit":
            break
        chat_code = input("Enter chat code: ")
        result = get_conversation_and_feedback(user_id, chat_code)
        print("Data extraction complete. Check .db file for results.")


