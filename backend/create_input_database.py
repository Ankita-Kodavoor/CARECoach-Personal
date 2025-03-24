import sqlite3
import os
import sys
from simplest_ranking import compute_final_rank, find_first_utterance
from freeform import get_freeform
import datetime
import traceback

# Import subskill_classifier directly from subskill.py with an alternate name
# to avoid conflicts with our wrapper function below
from subskill import subskill_classifier as original_classifier

from simplest_ranking import find_all_utterances

# Create a wrapper function with the same name that ensures the correct parameters are passed
def subskill_classifier(utterance, feedback=None):
    """
    Wrapper for the original subskill_classifier function that ensures
    both parameters are always provided.
    """
    # Ensure feedback is never None
    if feedback is None:
        feedback = ""
    
    try:
        # Call the original function with both parameters
        return original_classifier(utterance, feedback)
    except Exception as e:
        print(f"Error in subskill_classifier wrapper: {str(e)}")
        traceback.print_exc(file=sys.stderr)
        # Return a default value on error
        return "Using more open-ended questions/probes"

# existing database
DB_PATH = "saltcare.db" 
# new database 
NEW_DB_PATH = "test_input_v3.db"

def create_new_database():
    """Creates a new database to store extracted information."""
    conn = sqlite3.connect(NEW_DB_PATH)
    cursor = conn.cursor()
    
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
    
    # Create table for practice session with a UNIQUE constraint on (user_id, chat_code)
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
            utterance_rewind TEXT,
            current_state TEXT,
            state_history TEXT,
            UNIQUE(user_id, chat_code),
            FOREIGN KEY (target_utterance_id) REFERENCES extracted_conversation (id)
        )
    """)

    # Create table for practice session with a UNIQUE constraint on (user_id, chat_code)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_session_Z (
            practicesession_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            chat_code TEXT,
            target_skill TEXT,
            target_utterance_id INTEGER,
            utterance_feedback TEXT,
            utterance_alternative TEXT,
            user_context TEXT,
            target_subskill TEXT,
            utterance_rewind TEXT,
            UNIQUE(user_id, chat_code),
            FOREIGN KEY (target_utterance_id) REFERENCES extracted_conversation (id)
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS freeform_dialogue (
        practicesession_id INTEGER,
        practice_chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        utterance TEXT NOT NULL,
        role TEXT NOT NULL,
        state TEXT,
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (practicesession_id) REFERENCES practice_session (practicesession_id) ON DELETE CASCADE
    )
    """)
    
    # Modified subskill_map table to include feedback column
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subskill_map (
        practicesession_id INTEGER,
        utterance_id INTEGER NOT NULL,
        utterance TEXT NOT NULL,
        feedback TEXT,  -- New column for feedback
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
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (practice_chat_id) REFERENCES practice_session (practice_chat_id) ON DELETE CASCADE
    )
    """)
                   
    conn.commit()
    conn.close()

def store_extracted_data(conversation, feedback, user_id, chat_code):
    """Stores extracted data into the new database without calling the old workflow functions."""
    conn = sqlite3.connect(NEW_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")
        
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
        
        # Commit all changes at once
        cursor.execute("COMMIT")
        print(f"Successfully stored {len(conversation)} conversation entries and {len(feedback)} feedback entries")
        
    except Exception as e:
        # Rollback on error
        cursor.execute("ROLLBACK")
        print(f"Error storing extracted data: {str(e)}")
        traceback.print_exc()
        
    finally:
        conn.close()
    
    # No longer calling compute_and_store_target_skill() and populate_subskill_map() here
    # Those are now handled by the process_conversation_data() function

def process_conversation_data(user_id, chat_code):
    """
    Master function to handle the entire workflow:
    1. Compute target skill
    2. Populate subskill map with feedback
    3. Update practice session with first subskill
    """
    conn = sqlite3.connect(NEW_DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Step 1: Compute the target skill
        ranked_skills = compute_final_rank(user_id, chat_code)
        if not ranked_skills:
            print(f"No ranked skills found for user {user_id}, chat {chat_code}")
            return False
            
        target_skill = ranked_skills[0][0]
        print(f"Target skill identified: {target_skill}")
        
        # Create or update practice session with target skill
        cursor.execute("""
            INSERT OR REPLACE INTO practice_session (user_id, chat_code, target_skill)
            VALUES (?, ?, ?)
        """, (user_id, chat_code, target_skill))
        conn.commit()
        
        # Get the practice session ID
        cursor.execute("""
            SELECT practicesession_id FROM practice_session
            WHERE user_id = ? AND chat_code = ?
        """, (user_id, chat_code))
        ps_row = cursor.fetchone()
        if not ps_row:
            print(f"Failed to retrieve practice session ID")
            return False
            
        practicesession_id = ps_row[0]
        
        # Step 2: Find all flawed utterances for this skill
        flawed_utterance_ids = find_all_utterances(user_id, chat_code, target_skill)
        if not flawed_utterance_ids:
            print(f"No flawed utterances found for target skill: {target_skill}")
            return False
        
        print(f"Found {len(flawed_utterance_ids)} flawed utterances")
        
        # Step 3: Populate the subskill_map by looping through all flawed utterances
        for utterance_id in flawed_utterance_ids:
            # Get the utterance text
            cursor.execute("""
                SELECT utterance FROM extracted_conversation 
                WHERE id = ?
            """, (utterance_id,))
            utterance_row = cursor.fetchone()
            if not utterance_row:
                print(f"Utterance {utterance_id} not found, skipping")
                continue
                
            utterance_text = utterance_row[0]
            
            # Get the feedback for this utterance
            cursor.execute("""
                SELECT feedback FROM extracted_feedback
                WHERE utterance_id = ? AND chat_code = ?
                ORDER BY time DESC LIMIT 1
            """, (utterance_id, chat_code))
            feedback_row = cursor.fetchone()
            feedback_text = feedback_row[0] if feedback_row else ""
            
            # Classify the subskill using both utterance and feedback
            try:
                print(f"Classifying subskill for utterance ID {utterance_id}")
                target_subskill = subskill_classifier(utterance_text, feedback_text)
                print(f"Classified subskill: {target_subskill}")
                
                # Insert into subskill_map with the feedback
                cursor.execute("""
                    INSERT OR REPLACE INTO subskill_map 
                    (practicesession_id, utterance_id, utterance, feedback, subskill, completed)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (practicesession_id, utterance_id, utterance_text, feedback_text, target_subskill, False))
                
            except Exception as e:
                print(f"Error classifying subskill for utterance {utterance_id}: {str(e)}")
                continue
        
        conn.commit()
        
        # Step 4: Get the first flawed utterance (assuming they're ordered correctly)
        first_utterance_id = flawed_utterance_ids[0]
        
        # Get the subskill for this utterance from the subskill_map
        cursor.execute("""
            SELECT subskill FROM subskill_map
            WHERE practicesession_id = ? AND utterance_id = ?
        """, (practicesession_id, first_utterance_id))
        subskill_row = cursor.fetchone()
        if not subskill_row:
            print(f"No subskill found for first utterance {first_utterance_id}")
            return False
            
        first_subskill = subskill_row[0]
        
        # Get feedback and alternative for this utterance
        cursor.execute("""
            SELECT feedback, alternative FROM extracted_feedback
            WHERE utterance_id = ? AND chat_code = ?
            ORDER BY time DESC LIMIT 1
        """, (first_utterance_id, chat_code))
        fb_row = cursor.fetchone()
        feedback_val = fb_row[0] if fb_row else ""
        alternative_val = fb_row[1] if fb_row else ""
        
        # Build utterance_rewind (last 3 utterances up to and including target)
        cursor.execute("""
            SELECT role || ': ' || utterance
            FROM extracted_conversation
            WHERE chat_code = ? AND id <= ?
            ORDER BY id DESC
            LIMIT 3
        """, (chat_code, first_utterance_id))
        
        utterances = cursor.fetchall()
        utterances.reverse()  # Reverse to get ascending order
        utterance_rewind = ' '.join([row[0] for row in utterances]) if utterances else ""
        
        # Update practice_session with all the information
        cursor.execute("""
            UPDATE practice_session
            SET target_utterance_id = ?,
                target_subskill = ?,
                utterance_feedback = ?,
                utterance_alternative = ?,
                utterance_rewind = ?
            WHERE practicesession_id = ?
        """, (first_utterance_id, first_subskill, feedback_val, alternative_val, 
              utterance_rewind, practicesession_id))
        
        # Update user_context with conversation and feedback data
        cursor.execute("""
            UPDATE practice_session
            SET user_context = (
                SELECT json_object(
                    'User interaction', (
                        SELECT group_concat(role || ': ' || utterance, ' ')
                        FROM extracted_conversation
                        WHERE extracted_conversation.chat_code = practice_session.chat_code
                          AND extracted_conversation.id <= (practice_session.target_utterance_id + 1)
                    ),
                    'Feedback', (
                        SELECT json_group_array(feedback)
                        FROM extracted_feedback
                        WHERE extracted_feedback.chat_code = practice_session.chat_code
                          AND extracted_feedback.utterance_id = practice_session.target_utterance_id
                    ),
                    'Feedback area to focus', json_array(target_skill)
                )
            )
            WHERE practicesession_id = ?
        """, (practicesession_id,))
        
        conn.commit()
        print(f"Successfully updated practice session with target_subskill: {first_subskill}")
        
        # Verify the updates
        cursor.execute("""
            SELECT target_utterance_id, target_subskill, utterance_rewind
            FROM practice_session
            WHERE practicesession_id = ?
        """, (practicesession_id,))
        verify_row = cursor.fetchone()
        if verify_row:
            print(f"Verification - Target utterance ID: {verify_row[0]}")
            print(f"Verification - Target subskill: {verify_row[1]}")
            print(f"Verification - Utterance rewind length: {len(verify_row[2]) if verify_row[2] else 0}")
        
        return True
        
    except Exception as e:
        print(f"Error in process_conversation_data: {str(e)}")
        traceback.print_exc()
        return False
        
    finally:
        conn.close()

def get_conversation_data(user_id, chat_code):
    try:
        create_new_database() # Creating a new database
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

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
            # Assuming user_id represents the helper
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
        
        # Store the extracted data in the new database
        store_extracted_data(conversation_history, feedback_list, user_id, chat_code)
        
        # Run our new integrated workflow instead of the old functions
        success = process_conversation_data(user_id, chat_code)
        if success:
            print("Successfully processed conversation and populated subskill map")
        else:
            print("Warning: There was a problem processing the conversation data")

        return {"conversation": conversation_history, "feedback": feedback_list}
    except Exception as e:
        print(f"Error in get_conversation_data: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}

# The old functions are kept here for reference but are no longer used in the main workflow
def compute_and_store_target_skill(user_id, chat_code):
    """DEPRECATED: This function is no longer used in the main workflow."""
    print("WARNING: compute_and_store_target_skill is deprecated and should not be called directly")
    # Implementation removed to prevent accidental use

def populate_subskill_map(user_id, chat_code):
    """DEPRECATED: This function is no longer used in the main workflow."""
    print("WARNING: populate_subskill_map is deprecated and should not be called directly")
    # Implementation removed to prevent accidental use

if __name__ == "__main__":
    # Test the subskill classifier wrapper to make sure it's working
    try:
        test_result = subskill_classifier("This is a test utterance", "This is test feedback")
        print(f"Subskill classifier test result: {test_result}")
    except Exception as e:
        print(f"WARNING: Subskill classifier test failed: {str(e)}")
        traceback.print_exc()

    while True:
        user_id = input("Enter user ID (or type 'exit' to quit): ")
        if user_id.lower() == "exit":
            break
        chat_code = input("Enter chat code: ")
        result = get_conversation_data(user_id, chat_code)
        print("Data extraction complete. Check .db file for results.")