import sys
import sqlite3
from collections import defaultdict
import os

# Database path
DATABASE_PATH = os.path.abspath("saltcare.db") 

# Connect to the SQLite database
def connect_db(): 
    """Connect to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    return conn, cursor

# Predefined ranking scores based on ease criteria
EASE_SCORES = {
    "Professionalism": 8, "Structure": 7, "Validation": 6, "Questions": 5,
    "Reflections": 4, "Suggestions": 3, "Empathy": 2, "Self-Disclosure": 1
}

# Retrieve 'badareas' data from the feedback table
def get_badareas_data(therapist_id, chat_id):
    """Retrieve 'badareas' data from the feedback table."""
    conn, cursor = connect_db() # Connect to the database
    query = "SELECT utterance_id, badareas FROM feedback WHERE user_id = ? AND chat_code = ?" # query to get utterance_id and badareas
    cursor.execute(query, (therapist_id, chat_id)) 
    badareas_data = cursor.fetchall() # fetch all the data
    conn.close()
    return badareas_data

def parse_areas(areas_string):
    """Convert the 'badareas' field into a list of skills."""
    if not areas_string or areas_string.strip() in ["[]", "", "NULL"]: # check if the string is empty (strengths)
        return []
    return areas_string.replace("'", "").strip("[]").split(",") # if not (badareas) split the string and return the list

def compute_frequency_scores(therapist_id, chat_id):
    """Calculate the frequency score for each skill."""
    badareas_data = get_badareas_data(therapist_id, chat_id) # get the badareas data
    skill_counts = defaultdict(int) # initialize a dictionary to store the count of each skill
    
    for utterance_id, badareas in badareas_data: # iterate through the data
        if badareas:  # Ensure it's not empty
            skills = parse_areas(badareas)  # Convert string to list
            for skill in skills: # iterate through the skills
                skill_counts[skill.strip()] += 1  # Increment the count of the skill
    
    return skill_counts

def compute_final_rank(therapist_id, chat_id):
    """Rank skills based on frequency score, breaking ties using ease score."""
    frequency_scores = compute_frequency_scores(therapist_id, chat_id) # get the frequency scores
    
    # Create a list of tuples (skill, frequency_score, ease_score)
    rankings = [(skill, freq, EASE_SCORES.get(skill, 0)) for skill, freq in frequency_scores.items()]  # [('Validation', 3, 6), ('Questions', 5, 5)]
    
    # Sort first by frequency (descending), then by ease score (descending) in case of ties
    rankings.sort(key=lambda x: (-x[1], -x[2]))
    
    return rankings

def find_first_utterance(therapist_id, chat_id, target_skill): 
    """Finds the first utterance_id where the target skill is marked as a bad area."""
    badareas_data = get_badareas_data(therapist_id, chat_id)
    first_utterance_id = None

    for utterance_id, badareas in badareas_data:
        skills = parse_areas(badareas)
        if target_skill in skills:
            first_utterance_id = utterance_id
            break

    return first_utterance_id

def find_all_utterances(therapist_id, chat_id, target_skill):
    """
    Returns a list of all utterance_ids where the target_skill 
    is marked as a bad area.
    """
    badareas_data = get_badareas_data(therapist_id, chat_id)
    flawed_utterances = []

    for utterance_id, badareas in badareas_data:
        if not badareas:
            continue  # Skip if empty or None
        skills = parse_areas(badareas)
        if target_skill in skills:
            flawed_utterances.append(utterance_id)

    return flawed_utterances # returning a list of utterance_ids


if __name__ == "__main__":
    therapist_id = sys.argv[1]
    chat_id = sys.argv[2]
    
    ranked_skills = compute_final_rank(therapist_id, chat_id)
    
    print("\n====== Ranking Results ======\n")
    for skill, freq, ease in ranked_skills:
        print(f"{skill}: Frequency={freq}, Ease Score={ease}")

    print("Target Skill: ", ranked_skills[0][0])

    first_utterance_id = find_first_utterance(therapist_id, chat_id, ranked_skills[0][0])
    print("First Utterance ID with Target Skill: ", first_utterance_id)

    