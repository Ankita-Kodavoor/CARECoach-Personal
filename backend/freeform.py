import re
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv
import sqlite3
import datetime
import json
import traceback
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from response_scorer import score_and_update
from subskill_manager import (
    get_next_subskill, 
    mark_subskill_completed, 
    update_session_with_next_subskill,
    check_all_subskills_completed,
    get_subskill_progress
)

# Load environment variables and set up OpenAI
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
organization = os.getenv("OPENAI_ORGANIZATION")
project = os.getenv("OPENAI_PROJECT")

print(f"OpenAI API Key available: {bool(api_key)}", file=sys.stderr)
client = OpenAI(organization=organization, project=project, api_key=api_key)

# Set database path
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "test_input_v3.db")

# Default values for when data is missing
DEFAULT_SUBSKILL = "Using more open-ended questions/probes"
DEFAULT_CONTEXT = "Practice helping the client explore their concerns using open-ended questions."
DEFAULT_RESPONSE = "Hello! I'm here to help you practice your communication skills. How are you feeling today?"

# Define state transition mapping
STATE_TRANSITIONS = {
    "stage_A": {"continue": "stage_A", "completed": "stage_B"},
    "stage_B": {"continue": "stage_B", "completed": "stage_C"},
    "stage_C": {"continue": "stage_C", "completed": "stage_D"},
    "stage_D": {"continue": "stage_D", "completed": "stage_E"},
    "stage_E": {"continue": "stage_E", "completed": "stage_E"},
}

# Used for LLM structured outputs with Pydantic
class StateTransition(BaseModel):
    """
    Defines the structure for managing transitions between states in the dialogue module.
    """
    rationale: str = Field(
        ...,
        description="A concise explanation of the reasoning behind the selected state transition. This should clarify the rationale behind the transition decision."
    )
    transition: Literal["continue", "completed"] = Field(
        ...,
        description="Specifies the dialogue state transition. Use 'continue' to indicate that the task is still ongoing and requires further action, or 'completed' to signify that the task has been successfully finished and the dialogue state should advance."
    )

# Load system prompts
try:
    with open("./prompts/system_prompt_freeform.txt", "r") as file:
        SYSTEM_PROMPT_TEMPLATE = file.read()
    with open("./prompts/system_prompt_freeform_state.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_STATE = file.read()
    with open("./prompts/StageA.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_A = file.read()
    with open("./prompts/StageB.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_B = file.read()
    with open("./prompts/StageC.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_C = file.read()
    with open("./prompts/StageD.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_D = file.read()
    with open("./prompts/StageE.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_E = file.read()
    with open("./prompts/StageF.txt", "r") as file:
        SYSTEM_PROMPT_FREEFORM_F = file.read()
    print("Successfully loaded all prompt templates", file=sys.stderr)
except Exception as e:
    print(f"Error loading prompt templates: {str(e)}", file=sys.stderr)
    

def get_system_prompt_freeform(freeform_state, utterance_rewind, conversation_history, subskill, utterance_alternative):
    """Creates a system prompt by replacing placeholders in the template."""
    try:
        prompt = SYSTEM_PROMPT_TEMPLATE
        
        # Apply all replacements
        if freeform_state == "stage_A":
            print("Stage A", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_A)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{the goal}}", subskill)
            prompt = prompt.replace("{{alternative}}", utterance_alternative)
            prompt = prompt.replace("{{current_state}}", freeform_state)
        elif freeform_state == "stage_B":
            print("Stage B", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_B)
            prompt = prompt.replace("{{conversation_history}}", conversation_history)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{current_state}}", freeform_state)
        elif freeform_state == "stage_C":
            print("Stage C", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_C)
            prompt = prompt.replace("{{conversation_history}}", conversation_history)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{the goal}}", subskill)
            prompt = prompt.replace("{{current_state}}", freeform_state)
        elif freeform_state == "stage_D":
            print("Stage D", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_D)
            prompt = prompt.replace("{{conversation_history}}", conversation_history)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{the goal}}", subskill)
            prompt = prompt.replace("{{current_state}}", freeform_state)  
        elif freeform_state == "stage_E":
            print("Stage E", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_E)
            prompt = prompt.replace("{{conversation_history}}", conversation_history)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{the goal}}", subskill) 
            prompt = prompt.replace("{{current_state}}", freeform_state)  
        elif freeform_state == "stage_F":
            print("Stage F", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_F)
            prompt = prompt.replace("{{conversation_history}}", conversation_history)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{the goal}}", subskill)
            prompt = prompt.replace("{{current_state}}", freeform_state)
        else:
            # Default case if no valid stage is provided
            print(f"Unknown stage: {freeform_state}, using default", file=sys.stderr)
            prompt = prompt.replace("{{Instructions}}", SYSTEM_PROMPT_FREEFORM_A)
            prompt = prompt.replace("{{utterance_rewind}}", utterance_rewind)
            prompt = prompt.replace("{{conversation_history}}", conversation_history)
            prompt = prompt.replace("{{subskill}}", subskill)
            prompt = prompt.replace("{{the goal}}", subskill)
            prompt = prompt.replace("{{current_state}}", freeform_state)
        # Fill in any remaining unfilled placeholders to avoid errors
        prompt = prompt.replace("{{utterance_rewind}}", "No previous context available.")
        prompt = prompt.replace("{{conversation_history}}", "No conversation history available.")
        prompt = prompt.replace("{{subskill}}", DEFAULT_SUBSKILL)
        prompt = prompt.replace("{{the goal}}", DEFAULT_SUBSKILL)
        prompt = prompt.replace("{{current_state}}", freeform_state)
        return prompt
    except Exception as e:
        print(f"Error creating prompt: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "You are a helpful communication coach. Help the user practice their skills."


def get_state_classification_prompt(conversation_history, subskill, user_message, score, current_state):
    """Creates a state classification prompt to determine whether to continue or complete the current state."""
    try:
        # Load the state classification prompt from file
        try:
            with open("./prompts/state_classification_prompt.txt", "r") as file:
                state_classification_prompt = file.read()
        except FileNotFoundError:
            # If file doesn't exist, use default template
            state_classification_prompt = """
You are an AI therapy mentor who coaches novice therapists to upskill on foundational motivational interviewing skills.

Your task is to determine whether the current dialogue task has been achieved based on the conversation history provided. First, review the following dialogue history between you and the therapist you are coaching:

{{conversation_history}}

Now, consider the current dialogue task/stage that needs to be evaluated:
- Current stage: {{current_state}}
- Subskill focus: {{subskill}}
- User's latest message: {{user_message}}
- Current skill score: {{score}}

The stages in our learning flow are:
A. Introduction - Explaining the concept to master
B. MCQ Question - Presenting a multiple-choice question
C. MCQ Feedback - Providing feedback on the MCQ answer
D. Freeform Practice - Allowing free practice of the concept
E. Feedback and Continue - Providing feedback and moving to another practice scenario
F. Feedback and Stop - Final feedback and completion

Each stage has specific objectives:
- Stage A: The trainee should acknowledge understanding of the concept.
- Stage B: The trainee should answer the multiple-choice question.
- Stage C: The trainee should acknowledge the MCQ feedback.
- Stage D: The trainee should demonstrate application of the skill in 2-3 exchanges.
- Stage E: The trainee should reflect on feedback and express readiness for another scenario.
- Stage F: The trainee should acknowledge final feedback, demonstrating understanding of key takeaways.

You should evaluate whether the therapist has successfully achieved the current stage's task based on the provided dialogue history.

You must provide your decision in a JSON format with the following structure:
{
  "rationale": "A concise explanation of your reasoning",
  "transition": "Either 'continue' if the task is ongoing or 'completed' if the task has been successfully completed"
}

Transition Guidelines:
- Use 'continue' when the therapist needs more practice or hasn't fully demonstrated understanding of the current stage
- Use 'completed' when the therapist has demonstrated sufficient understanding and is ready to move to the next stage

If the user explicitly asks to move to a different stage or skip ahead, you should recognize this request but still base your transition decision on whether they've met the learning objectives of the current stage.
"""
        
        # Replace placeholders
        state_classification_prompt = state_classification_prompt.replace("{{conversation_history}}", conversation_history)
        state_classification_prompt = state_classification_prompt.replace("{{subskill}}", subskill)
        state_classification_prompt = state_classification_prompt.replace("{{user_message}}", user_message)
        state_classification_prompt = state_classification_prompt.replace("{{score}}", score)
        state_classification_prompt = state_classification_prompt.replace("{{current_state}}", current_state)
        
        return state_classification_prompt
    except Exception as e:
        print(f"Error creating state classification prompt: {str(e)}", file=sys.stderr)
        # Use a default prompt if file loading fails
        return """You are analyzing dialogue between a therapy mentor and therapist trainee.
Consider the conversation history and determine if the current stage ({current_state}) 
is completed or should continue. Return either "continue" or "completed".
Conversation history: {conversation_history}
Current stage: {current_state}
Last user message: {user_message}
""".format(conversation_history=conversation_history, current_state=current_state, user_message=user_message)


def fetch_session_data(user_id, chat_code):
    """Fetch all necessary data for a practice session in one query."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get comprehensive session data in a single query, including utterance_rewind
        cursor.execute("""
            SELECT 
                ps.practicesession_id, 
                ps.target_utterance_id, 
                ps.utterance_alternative,
                ps.target_subskill,
                ps.user_context,
                ps.utterance_rewind,
                ps.current_state,
                ps.state_history
            FROM practice_session ps
            WHERE ps.user_id = ? AND ps.chat_code = ?
            LIMIT 1
        """, (user_id, chat_code))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            print(f"[ERROR] No practice session found for user_id: '{user_id}', chat_code: '{chat_code}'", file=sys.stderr)
            return {
                "practicesession_id": None,
                "target_utterance_id": None,
                "utterance_alternative": None,
                "target_subskill": DEFAULT_SUBSKILL,
                "user_context": DEFAULT_CONTEXT,
                "utterance_rewind": "",
                "current_state": "default",
                "state_history": "default"
            }
            
        practicesession_id, target_utterance_id, utterance_alternative, target_subskill, user_context, utterance_rewind, current_state, state_history = row
        return {
            "practicesession_id": practicesession_id,
            "target_utterance_id": target_utterance_id or -1,
            "utterance_alternative": utterance_alternative,
            "target_subskill": target_subskill or DEFAULT_SUBSKILL,
            "user_context": user_context or DEFAULT_CONTEXT,
            "utterance_rewind": utterance_rewind or "",
            "current_state": current_state or "default",
            "state_history": state_history or "default"
        }
    
    except Exception as e:
        print(f"[ERROR] Exception in fetch_session_data: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {
            "practicesession_id": None, 
            "target_utterance_id": None,
            "utterance_alternative": None,
            "target_subskill": DEFAULT_SUBSKILL,
            "user_context": DEFAULT_CONTEXT,
            "utterance_rewind": "",
            "current_state": "default",
            "state_history": "default"
        }


def get_last_user_message(practicesession_id):
    """Retrieves the most recent user message."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT utterance
            FROM freeform_dialogue
            WHERE practicesession_id = ? AND role = 'user'
            ORDER BY time DESC
            LIMIT 1
        """, (practicesession_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    except Exception as e:
        print(f"Error in get_last_user_message: {str(e)}", file=sys.stderr)
        return None


def store_freeform_dialogue(practicesession_id, message, role='system', state=None):
    """
    Inserts a new row into freeform_dialogue.
    - If role='user', we look up the user_id from practice_session.
    - If role='system', we use 'system' as the user_id.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get user_id from practice_session if role is user
        if role == 'user':
            cursor.execute("SELECT user_id FROM practice_session WHERE practicesession_id = ?", 
                          (practicesession_id,))
            row = cursor.fetchone()
            if not row:
                print(f"No user_id found for practicesession_id: {practicesession_id}", file=sys.stderr)
                conn.close()
                return False
            user_id = row[0]
        else:
            user_id = 'system'
        
        # Insert the message
        cursor.execute("""
            INSERT INTO freeform_dialogue 
            (practicesession_id, user_id, utterance, role, state) 
            VALUES (?, ?, ?, ?, ?)
        """, (practicesession_id, user_id, message, role, state))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error in store_freeform_dialogue: {str(e)}", file=sys.stderr)
        return False


def get_conversation_history(practicesession_id):
    """Retrieves formatted conversation history."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, utterance FROM freeform_dialogue
            WHERE practicesession_id = ?
            ORDER BY time ASC
        """, (practicesession_id,))
        
        conversation_rows = cursor.fetchall()
        conn.close()
        return "\n".join([f"{role}: {utterance}" for role, utterance in conversation_rows])
    except Exception as e:
        print(f"Error retrieving conversation history: {str(e)}", file=sys.stderr)
        return ""


async def classify_state_transition(conversation_history, subskill, user_message, score, current_state):
    """
    Determines whether to continue in the current state or transition to the next state.
    Using Pydantic for structured output.
    
    Returns:
        str: Either "continue" or "completed"
    """
    try:
        prompt = get_state_classification_prompt(conversation_history, subskill, user_message, score, current_state)
        
        if not api_key:
            print("OpenAI API key not available, defaulting to 'continue'", file=sys.stderr)
            return "continue"
        
        # Using structured output with the StateTransition model
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        response_content = response.choices[0].message.content
        print(f"Raw state classification response: {response_content}", file=sys.stderr)
        
        try:
            # Parse the JSON response into the Pydantic model
            result_dict = json.loads(response_content)
            result = StateTransition(**result_dict)
            
            # Log the classification details
            print(f"State transition classification: {result.transition}", file=sys.stderr)
            print(f"Classification rationale: {result.rationale}", file=sys.stderr)
            
            return result.transition
            
        except Exception as json_error:
            print(f"Error parsing state transition: {str(json_error)}", file=sys.stderr)
            # Fallback parsing
            if "continue" in response_content.lower():
                return "continue"
            elif "completed" in response_content.lower():
                return "completed"
            else:
                print(f"Could not parse transition, defaulting to 'continue'", file=sys.stderr)
                return "continue"
            
    except Exception as e:
        print(f"Error classifying state transition: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "continue"  # Default to continue on error


def get_next_state(current_state, transition_decision, practicesession_id=None):
    """
    Determines the next state based on the current state and transition decision.
    Also handles subskill transitions when a subskill is completed.
    
    Args:
        current_state: The current state (e.g., 'stage_A')
        transition_decision: Either 'continue' or 'completed'
        practicesession_id: Optional ID of the practice session for subskill management
        
    Returns:
        str: The next state
    """
    if current_state not in STATE_TRANSITIONS:
        print(f"Unknown state '{current_state}', defaulting to stage_A", file=sys.stderr)
        current_state = "stage_A"
    
    # Get the default next state based on the transition decision
    next_state = STATE_TRANSITIONS[current_state][transition_decision]
    
    # Special handling for stage_E when completed - move to the next subskill
    if current_state == "stage_E" and transition_decision == "completed" and practicesession_id:
        # Try to update the session with the next subskill
        if update_session_with_next_subskill(practicesession_id):
            # Successfully moved to the next subskill, go back to stage_A
            print(f"Moving to next subskill for practice session ID: {practicesession_id}", file=sys.stderr)
            return "stage_A"  # Override the next state to start the new subskill
    
    # Special handling for stage_F - this is our terminal state
    # If we complete stage_F, check if we have any remaining subskills
    if current_state == "stage_F" and transition_decision == "completed" and practicesession_id:
        if not check_all_subskills_completed(practicesession_id):
            # We still have more subskills to work on
            if update_session_with_next_subskill(practicesession_id):
                print(f"Moving to next subskill from stage_F for session ID: {practicesession_id}", file=sys.stderr)
                return "stage_A"  # Move to stage_A with the next subskill
    
    return next_state


def update_practice_session_state(practicesession_id, state, transition_decision=None, transition_rationale=None):
    """
    Updates the current state and appends to stage history in the practice_session table.
    Records every state change, including repeated states.
    
    Args:
        practicesession_id: The ID of the practice session
        state: The current freeform state (e.g., 'stage_A', 'stage_B', etc.)
        transition_decision: Optional transition decision for logging
        transition_rationale: Optional rationale for the transition
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current history (if any)
        cursor.execute("""
            SELECT state_history 
            FROM practice_session 
            WHERE practicesession_id = ?
        """, (practicesession_id,))
        
        row = cursor.fetchone()
        if not row:
            print(f"No practice session found with ID: {practicesession_id}", file=sys.stderr)
            conn.close()
            return False
            
        state_history = row[0]
        
        # Current timestamp
        timestamp = datetime.datetime.now().isoformat()
        
        # Parse existing history or create new
        history_data = []
        if state_history:
            try:
                history_data = json.loads(state_history)
            except json.JSONDecodeError:
                # If history is corrupted, start fresh
                history_data = []
        
        # Append new state with timestamp and transition info if provided
        entry = {"state": state, "timestamp": timestamp}
        if transition_decision:
            entry["transition"] = transition_decision
        if transition_rationale:
            entry["rationale"] = transition_rationale
            
        history_data.append(entry)
        
        # Convert back to JSON string
        new_history = json.dumps(history_data)
        
        # Update practice_session table
        cursor.execute("""
            UPDATE practice_session 
            SET current_state = ?, state_history = ? 
            WHERE practicesession_id = ?
        """, (state, new_history, practicesession_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating practice session state: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False



async def get_freeform(user_id, chat_code):
    """Main function to generate scenario or feedback based on conversation state."""
    try:
        print(f"Getting freeform for user_id: {user_id}, chat_code: {chat_code}", file=sys.stderr)
        
        # Get session data with all necessary fields in one query
        session_data = fetch_session_data(user_id, chat_code)
        if not session_data["practicesession_id"]:
            print(f"[WARNING] Using default response due to missing session data", file=sys.stderr)
            return DEFAULT_RESPONSE, False
            
        practicesession_id = session_data["practicesession_id"]
        target_subskill = session_data["target_subskill"]
        utterance_rewind = session_data["utterance_rewind"]
        utterance_alternative = session_data["utterance_alternative"]
        current_state = session_data["current_state"]
        state_history = session_data["state_history"]
        
        # Handle completed state with consistent completion message
        if current_state == "completed" or check_all_subskills_completed(practicesession_id):
            # If we're completed or just detected completion, ensure state is updated
            if current_state != "completed":
                update_practice_session_state(practicesession_id, "completed")
                
            completion_message = "Congratulations on completing your learning session! You've successfully worked through all the practice materials and demonstrated understanding of the key concepts."
            store_freeform_dialogue(practicesession_id, completion_message, 'system', state="completed")
            return completion_message, False
        
        # Default to stage_A if no valid state
        if not current_state or current_state == "default":
            current_state = "stage_A"
        
        # Check if we need to initialize the first subskill
        if not target_subskill or target_subskill == DEFAULT_SUBSKILL:
            # Try to get the first available subskill
            next_subskill_data = get_next_subskill(practicesession_id)
            if next_subskill_data:
                # Update the session with the first subskill
                update_session_with_next_subskill(practicesession_id)
                # Refresh session data
                session_data = fetch_session_data(user_id, chat_code)
                target_subskill = session_data["target_subskill"]
                print(f"Updating session with next subskill: {target_subskill}", file=sys.stderr)
                utterance_rewind = session_data["utterance_rewind"]
        
        print(f"Current state: {current_state}", file=sys.stderr)
        print(f"State history: {state_history}", file=sys.stderr)

        # Get conversation history
        conversation_history = get_conversation_history(practicesession_id)
        
        # Get user message (or empty string if none)
        user_message = get_last_user_message(practicesession_id) or ""
        
        print(f"User message: {user_message[:50]}{'...' if len(user_message) > 50 else ''}", file=sys.stderr)
        print(f"Subskill: {target_subskill}", file=sys.stderr)
        
        # Check if we have an OpenAI API key
        if not api_key:
            print("OpenAI API key not available, using default response", file=sys.stderr)
            # Store default response in dialogue
            store_freeform_dialogue(practicesession_id, DEFAULT_RESPONSE, 'system', state=current_state)
            return DEFAULT_RESPONSE, False
        
        # Score the conversation
        score = score_and_update(practicesession_id, conversation_history, user_message)
        print(f"Score: {score}", file=sys.stderr)

        # Determine state transition (continue or completed) using pydantic
        transition_decision = await classify_state_transition(
            conversation_history, 
            target_subskill, 
            user_message, 
            str(score),
            current_state
        )
        print(f"Transition decision: {transition_decision}", file=sys.stderr)
        
        # Get the next state based on the transition decision, passing practicesession_id
        next_state = get_next_state(current_state, transition_decision, practicesession_id)
        print(f"Transitioning from {current_state} to {next_state}", file=sys.stderr)
        
        # Update the practice_session table with the new state
        update_practice_session_state(
            practicesession_id, 
            next_state, 
            transition_decision
        )
        
        # Check if all subskills have been completed when reaching stage_E
        all_completed = False
        should_force_next_subskill = False
        if next_state == "stage_E":
            progress = get_subskill_progress(practicesession_id)
            completed_count = progress.get('completed', 0)
            total_count = progress.get('total', 0)
            remaining_subskills = len(progress.get('remaining', []))
            
            print(f"Subskill progress: {completed_count}/{total_count} completed, {remaining_subskills} remaining", 
                  file=sys.stderr)
            
            if remaining_subskills > 0:
                # Still have more subskills to go through
                should_force_next_subskill = True
                print(f"Will transition to next subskill after stage_E message. {remaining_subskills} subskills remaining.", 
                      file=sys.stderr)
            elif completed_count > 0 and completed_count == total_count:
                # All subskills are completed
                all_completed = True
                print("All subskills completed! Will send congratulatory message.", file=sys.stderr)
        
        # If all subskills are completed, send congratulatory message
        if all_completed:
            completion_message = "Congratulations on completing your learning session! You've successfully worked through the practice of asking the right open-ended questions, a critical skill in counselling."
            store_freeform_dialogue(practicesession_id, completion_message, 'system', state=next_state)
            
            # Update the session state to "completed" to avoid re-entering the workflow
            update_practice_session_state(practicesession_id, "completed")
            return completion_message, False
        
        # Create prompt using the next state
        prompt = get_system_prompt_freeform(
            next_state, 
            utterance_rewind, 
            conversation_history, 
            target_subskill,
            utterance_alternative
        )

        # Generate response with proper error handling
        try:
            # Make API request 
            response_values = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message or "Hello"}
                ],
            )

            # Get content from response
            content = response_values.choices[0].message.content.strip()
            print(f"Content: {content[:100]}...", file=sys.stderr)
            
            # Store the system response in the database
            store_freeform_dialogue(practicesession_id, content, 'system', state=next_state)
            
            # Update score after response
            updated_conversation = get_conversation_history(practicesession_id)
            updated_score = score_and_update(practicesession_id, updated_conversation, user_message)
            print(f"Updated score: {updated_score}", file=sys.stderr)
            
            return content, should_force_next_subskill
                
        except Exception as api_error:
            error_msg = str(api_error)
            print(f"OpenAI API error: {error_msg}", file=sys.stderr)
            
            # Create a helpful fallback response based on the state
            fallback = f"I'm here to help with your {target_subskill} practice. How would you like to proceed?"
            store_freeform_dialogue(practicesession_id, fallback, 'system', state=next_state)
            return fallback, should_force_next_subskill
            
    except Exception as e:
        print(f"Error in get_freeform: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "I'm here to help with your communication practice. Let's have a conversation!", False


async def get_next_subskill_message(user_id, chat_code):
    """Special function to generate message for the next subskill after stage_E."""
    try:
        # Get session data
        session_data = fetch_session_data(user_id, chat_code)
        if not session_data["practicesession_id"]:
            return "Let's continue with the next skill."
            
        practicesession_id = session_data["practicesession_id"]
        old_subskill = session_data["target_subskill"]
        current_state = session_data["current_state"]
        
        # Check if session is already in completed state
        if current_state == "completed":
            completion_message = "Congratulations on completing your learning session! You've successfully worked through all the practice materials and demonstrated understanding of the key concepts."
            # Don't need to store in dialogue as get_freeform would have already done this
            return completion_message
        
        # Check if all subskills are already completed
        if check_all_subskills_completed(practicesession_id):
            completion_message = "Congratulations on completing your learning session! You've successfully worked through all the practice materials and demonstrated understanding of the key concepts."
            # Update the session state to "completed"
            update_practice_session_state(practicesession_id, "completed")
            store_freeform_dialogue(practicesession_id, completion_message, 'system', state="completed")
            return completion_message
        
        # Mark current subskill as completed
        mark_subskill_completed(practicesession_id, old_subskill)
        
        # Update to next subskill - this returns False if all subskills are completed
        success = update_session_with_next_subskill(practicesession_id)
        
        # Check if the update to next subskill resulted in completing all skills
        # This happens when we mark the last subskill as completed
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT current_state FROM practice_session WHERE practicesession_id = ?", 
                      (practicesession_id,))
        current_state = cursor.fetchone()[0]
        conn.close()
        
        # If the session is now in completed state or the update failed because all subskills are done
        if current_state == "completed" or not success:
            completion_message = "Congratulations on completing your learning session! You've successfully worked through all the practice materials and demonstrated understanding of the key concepts."
            store_freeform_dialogue(practicesession_id, completion_message, 'system', state="completed")
            return completion_message
        
        # Refresh session data to get the new subskill
        session_data = fetch_session_data(user_id, chat_code)
        new_subskill = session_data["target_subskill"]
        utterance_rewind = session_data["utterance_rewind"]
        print(f"New subskill: {new_subskill} and Old subskill: {old_subskill}", file=sys.stderr)
        
        # Update state to stage_A
        update_practice_session_state(
            practicesession_id, 
            "stage_A",
            "auto_transition"
        )
        
        # Get conversation history
        conversation_history = get_conversation_history(practicesession_id)
        
        # Create prompt for stage_A
        prompt = get_system_prompt_freeform(
            "stage_A", 
            utterance_rewind, 
            conversation_history, 
            new_subskill,
            session_data["utterance_alternative"]
        )
        
        try:
            # Generate new subskill introduction
            response_values = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Let's start learning about {new_subskill}"}
                ],
            )
            
            # Get content from response
            content = response_values.choices[0].message.content.strip()
            
            # Add transition message
            final_content = f"Great work on practicing {old_subskill}! Now let's move on to the next skill.\n\n{content}"
            
            # Store in dialogue
            store_freeform_dialogue(practicesession_id, final_content, 'system', state="stage_A")
            
            return final_content
            
        except Exception as api_error:
            error_msg = str(api_error)
            print(f"OpenAI API error generating next subskill message: {error_msg}", file=sys.stderr)
            
            # Fallback message
            fallback = f"Great job with {old_subskill}! Let's now work on {new_subskill}."
            store_freeform_dialogue(practicesession_id, fallback, 'system', state="stage_A")
            return fallback
            
    except Exception as e:
        print(f"Error in get_next_subskill_message: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "Let's continue with the next skill."