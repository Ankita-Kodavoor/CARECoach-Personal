import sqlite3
import sys
import json
import traceback
import os

def get_unique_subskills(practicesession_id):
    """
    Gets a list of all unique subskills for a practice session.
    Returns a list of dicts containing subskill info, with each unique subskill appearing only once.
    The utterance_id will be the last (highest) utterance_id for that subskill.
    """
    try:
        # Get database path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(current_dir, "test_input_v3.db")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Use a subquery to get the latest utterance_id for each subskill
        cursor.execute("""
            SELECT sm.utterance_id, sm.utterance, sm.subskill, sm.completed
            FROM subskill_map sm
            INNER JOIN (
                SELECT subskill, MAX(utterance_id) as max_utterance_id
                FROM subskill_map
                WHERE practicesession_id = ?
                GROUP BY subskill
            ) latest_sm ON sm.subskill = latest_sm.subskill AND sm.utterance_id = latest_sm.max_utterance_id
            WHERE sm.practicesession_id = ?
            ORDER BY sm.utterance_id
        """, (practicesession_id, practicesession_id))
        
        unique_subskills = []
        for row in cursor.fetchall():
            utterance_id, utterance, subskill, completed = row
            unique_subskills.append({
                "utterance_id": utterance_id, 
                "utterance": utterance, 
                "subskill": subskill,
                "completed": completed == 1
            })
        
        conn.close()
        return unique_subskills
        
    except Exception as e:
        print(f"Error in get_unique_subskills: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return []

def get_next_subskill(practicesession_id, current_subskill=None):
    """
    Finds the next incomplete unique subskill for a given practice session.
    If current_subskill is provided, finds the next one after that.
    Returns subskill details or None if no incomplete subskills are available.
    """
    try:
        # Get unique subskills for this practice session
        unique_subskills = get_unique_subskills(practicesession_id)
        
        # Filter out completed subskills
        incomplete_subskills = [s for s in unique_subskills if not s["completed"]]
        
        if not incomplete_subskills:
            print(f"No incomplete subskills found for practice session ID: {practicesession_id}", file=sys.stderr)
            return None
            
        # If current_subskill is not specified, return the first incomplete subskill
        if current_subskill is None:
            return incomplete_subskills[0]
        
        # If current_subskill is specified, find the next one in the list
        current_found = False
        for subskill_info in incomplete_subskills:
            if current_found:
                # Return the next subskill after the current one
                return subskill_info
            
            # Check if this is the current subskill
            if subskill_info["subskill"] == current_subskill:
                current_found = True
        
        # If we've gone through all subskills and didn't find a next one,
        # return the first one for a loop
        if current_found and incomplete_subskills:
            return incomplete_subskills[0]
        
        # If the current subskill wasn't found at all, return the first incomplete subskill
        if incomplete_subskills:
            return incomplete_subskills[0]
        
        return None
        
    except Exception as e:
        print(f"Error in get_next_subskill: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def mark_subskill_completed(practicesession_id, subskill):
    """
    Marks a subskill as completed in the subskill_map table.
    Only marks the specific subskill string as completed, not all instances.
    Returns True if successful, False otherwise.
    """
    try:
        # Get database path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(current_dir, "test_input_v3.db")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update the completed status for all instances of this subskill
        cursor.execute("""
            UPDATE subskill_map
            SET completed = 1
            WHERE practicesession_id = ? AND subskill = ?
        """, (practicesession_id, subskill))
        
        conn.commit()
        affected_rows = cursor.rowcount
        conn.close()
        
        if affected_rows > 0:
            print(f"Marked subskill '{subskill}' as completed for practice session ID: {practicesession_id}", 
                  file=sys.stderr)
            return True
        else:
            print(f"No matching subskill '{subskill}' found for practice session ID: {practicesession_id}", 
                  file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"Error in mark_subskill_completed: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False


def get_subskill_progress(practicesession_id):
    """
    Retrieves the progress of unique subskills for a given practice session.
    Returns a dictionary with completed and total counts.
    """
    try:
        # Get unique subskills for this practice session
        unique_subskills = get_unique_subskills(practicesession_id)
        
        if not unique_subskills:
            return {"completed": 0, "total": 0, "percentage": 0}
        
        # Count completed subskills
        total_subskills = len(unique_subskills)
        completed_subskills = sum(1 for s in unique_subskills if s["completed"])
        
        return {
            "completed": completed_subskills,
            "total": total_subskills,
            "percentage": round((completed_subskills / total_subskills * 100), 2) if total_subskills > 0 else 0,
            "remaining": [s["subskill"] for s in unique_subskills if not s["completed"]]
        }
        
    except Exception as e:
        print(f"Error in get_subskill_progress: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {"completed": 0, "total": 0, "percentage": 0, "remaining": []}


def get_current_subskill(practicesession_id):
    """
    Retrieves the current subskill being worked on in the practice session.
    Returns the subskill or None if no subskill is set.
    """
    try:
        # Get database path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(current_dir, "test_input_v3.db")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get the current subskill from the practice_session table
        cursor.execute("""
            SELECT target_subskill 
            FROM practice_session
            WHERE practicesession_id = ?
        """, (practicesession_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return row[0]
        else:
            return None
            
    except Exception as e:
        print(f"Error in get_current_subskill: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def update_session_with_next_subskill(practicesession_id):
    """
    Updates the practice session with the next available subskill.
    Returns True if successful, False otherwise.
    """
    try:
        # Get the current subskill
        current_subskill = get_current_subskill(practicesession_id)
        
        # Mark the current subskill as completed (if it exists)
        if current_subskill:
            mark_subskill_completed(practicesession_id, current_subskill)
        
        # Check if all subskills are completed
        if check_all_subskills_completed(practicesession_id):
            print(f"All subskills are completed for practice session ID: {practicesession_id}", file=sys.stderr)
            # Update the practice session to set a special "completed" state
            current_dir = os.path.dirname(os.path.abspath(__file__))
            DB_PATH = os.path.join(current_dir, "test_input_v3.db")
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE practice_session
                SET current_state = 'completed'
                WHERE practicesession_id = ?
            """, (practicesession_id,))
            
            conn.commit()
            conn.close()
            return False
        
        # Get the next available subskill
        next_subskill_data = get_next_subskill(practicesession_id, current_subskill)
        
        if not next_subskill_data:
            print(f"No next subskill available for practice session ID: {practicesession_id}", file=sys.stderr)
            return False
        
        # Get database path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(current_dir, "test_input_v3.db")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update the practice session with the next subskill
        cursor.execute("""
            UPDATE practice_session
            SET target_subskill = ?,
                target_utterance_id = ?,
                utterance_rewind = ?
            WHERE practicesession_id = ?
        """, (
            next_subskill_data["subskill"],
            next_subskill_data["utterance_id"],
            next_subskill_data["utterance"],
            practicesession_id
        ))
        
        conn.commit()
        conn.close()
        
        print(f"Updated practice session ID: {practicesession_id} with next subskill: {next_subskill_data['subskill']}", 
              file=sys.stderr)
        return True
        
    except Exception as e:
        print(f"Error in update_session_with_next_subskill: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False


def check_all_subskills_completed(practicesession_id):
    """
    Checks if all unique subskills for a practice session have been completed.
    Returns True if all completed, False otherwise.
    """
    progress = get_subskill_progress(practicesession_id)
    return progress["completed"] == progress["total"] and progress["total"] > 0