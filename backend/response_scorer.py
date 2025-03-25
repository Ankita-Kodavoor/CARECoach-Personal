"""
simple_response_scorer.py - Minimal OpenAI-based response scoring
"""
import os
import sys
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables for OpenAI
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# organization = os.getenv("OPENAI_ORGANIZATION")
# project parameter is not supported in the new OpenAI client
# project = os.getenv("OPENAI_PROJECT")
 # organization=organization
# Initialize OpenAI client with only supported parameters

client = OpenAI()


# Set database path
current_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(current_dir, "test_input_v3.db")

def score_response(conversation_history):
    """
    Uses OpenAI to score a response as 1 (good) or 0 (bad)
    
    Args:
        response_text: The text response to evaluate
        
    Returns:
        int: 1 for good response, 0 for bad response
    """
    try:
        # if not api_key:
        #     print("OpenAI API key not available, using basic scoring", file=sys.stderr)
        #     # Fallback to basic scoring
        #     return 1 if len(response_text.split()) > 20 else 0
            
        system_prompt = """You are evaluating responses by a therapist with a numerical score. Look at the last response by the user in the {{conversation_history}}. You have already generated a response to the user's message. Using the assessment you made,
         you are now storing your feedback as either 1 (good) or 0 (bad). If you gave the user a suggestion on how to improve their response, then score it as a 0.
         If you assessed that the user's response was good, then score it as a 1. If you assessed that the user's response was unrelated to the topic at hand or that you had not 
         specifically given feedback to a response by the user, then score it as a Null.

        A good response (1):
        - The response specifically gave feedback to the user's response.
        - The response stated that the user's response was good and on the right track.
        - If it says anything along the line of good jodb, or great work, or you got it right, then score it as a 1.

        A bad response (0):
        - If the response states that the therapist's response needed improvement, then score it as a 0.
        - If there is a suggestion on how the therapist can improve the response, then score it as a 0.
        ##Characteristics that make questions wrong
        1. Making questions too focused in situations in which they should be more open-ended
        2. Asking "why" questions in exploration phase, because they are difficult to answer and can make the client defensive.
        3. Asking questions without empathy
        4. Asking lengthy or multiple questions at once
        5. Turning the attention to other people instead of the seeker (i.e., asking what person X did, instead of asking how the seeker felt about X's behavior)


        If the response does not indicate good or bad feedback then score it as a Null. An example of a response that includes feedback is "Great job!" or "Asking why questions makes the user feel judged. Try...".
        If the response does not explicitly contain feedback for the user then score it as a Null.
        For example, if the response only includes a new patient scenario with no feedback to the user on their response, then score it as a Null.

        You're only job is to assign a numerical score to the response. Do NOT explain your reasoning, since we need a single numerical score.
        Respond with ONLY the number Null, 1 or 0.
        Only return one number. Do not return more than one number. 

        Example outputs:
        Null
        1
        0

        Example inputs/outputs:
        Input:
        System scenario: I'm feeling really down today.
        User: That sounds difficult. Can you share more about what you're experiencing?
        Output: 1

        Input:
        System scenario: I'm feeling really down today.
        User: Why do you feel down?
        Output: 0

        Input:
        System scenario: I'm feeling really down today.
        User: Let's continue or New scenario
        Output: Null
        """

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o",  # Using smaller model for efficiency
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Assign a numerical score based on the feedback you gave the user:\n\n{conversation_history}"}
            ],
            max_tokens=5,  # We only need a single digit
            temperature=0.4  # Keep it consistent
        )
        
        # Extract just the first digit (0 or 1)
        score_text = response.choices[0].message.content.strip()
        print(score_text)

        if "Null" in score_text:
            print(f"Score: {score_text}", file=sys.stderr)
            return None
        elif "1" in score_text:
            print(f"Score: {score_text}", file=sys.stderr)
            return 1
        elif "0" in score_text:
            print(f"Score: {score_text}", file=sys.stderr)
            return 0
        else:
            print(f"Couldn't extract score from: {score_text}", file=sys.stderr)
            return None  # Default to None if parsing fails
            
    except Exception as e:
        print(f"Error in score_response: {str(e)}", file=sys.stderr)
        return None  # Default to None on error


def update_last_user_score(practicesession_id, score, utterance):
    """
    Updates the most recent 'user' row for this practice session to set the 'score' column.
    If no matching record exists in score_history, creates a new one.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # First, get the most recent practice_chat_id
        cursor.execute("""
            SELECT practice_chat_id
            FROM freeform_dialogue
            WHERE practicesession_id = ?
            AND role = 'user'
            ORDER BY practice_chat_id DESC
            LIMIT 1
        """, (practicesession_id,))
        
        result = cursor.fetchone()
        if not result:
            print(f"No user messages found for practice session {practicesession_id}", file=sys.stderr)
            conn.close()
            return False
            
        practice_chat_id = result[0]
        
        # Try to update existing record
        cursor.execute("""
            UPDATE score_history
            SET score = ?, utterance = ?
            WHERE practice_chat_id = ?
        """, (score, utterance, practice_chat_id))
        
        # If no rows were affected, insert a new record
        if cursor.rowcount == 0:
            cursor.execute("""
                INSERT INTO score_history (practice_chat_id, practicesession_id, score, utterance)
                VALUES (?, ?, ?, ?)
            """, (practice_chat_id, practicesession_id, score, utterance))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error in update_last_user_score: {str(e)}", file=sys.stderr)
        return False

def score_and_update(practicesession_id, conversation_history, utterance):
    """
    Complete function that scores a response and updates the database
    
    Args:
        practicesession_id: ID of the practice session
        response_text: Text response to evaluate
        
    Returns:
        int: The assigned score (0 or 1)
    """
    # Get the score
    score = score_response(conversation_history)
    # Update the database
    update_last_user_score(practicesession_id, score, utterance)
    return score

# # Example usage
# if __name__ == "__main__":
#     # Example response
#     example_response = "I hear your concerns. Let's explore this further."
    
#     # Example practice session ID - replace with a valid ID for testing
#     example_id = 1
    
#     # Score and update
#     result = score_and_update(example_id, example_response)
#     print(f"Response scored: {result}")