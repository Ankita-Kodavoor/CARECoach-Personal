from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DB_PATH = "saltcare_personal.db"  # Path to your SQLite database

def get_db_connection():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Allows fetching results as dictionaries
    return conn

@app.route('/api/session/<string:chat_code>', methods=['GET'])
def get_session(chat_code):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch data only from the practice_session table
        cursor.execute("""
            SELECT 
                practicesession_id, user_id, target_skill, target_utterance_id, 
                utterance_feedback, utterance_alternative, user_context, target_subskill
            FROM practice_session
            WHERE chat_code = ?
        """, (chat_code,))
        
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Chat code not found in practice_session'}), 404

        # Prepare JSON response
        session_data = {
            'practiceSessionId': row['practicesession_id'],
            'userId': row['user_id'],
            'chatCode': chat_code,
            'targetSkill': row['target_skill'],
            'targetUtteranceId': row['target_utterance_id'],
            'knowledgeBite': {
                'concept': row['target_subskill'],
                'description': row['utterance_feedback']
            },
            'mcq': {
                'clientStatement': row['utterance_alternative'],  # Assuming this is the MCQ question
                'options': [
                    {'id': 'A', 'text': "Option 1"},  # Placeholder, update with real options if available
                    {'id': 'B', 'text': "Option 2"},
                    {'id': 'C', 'text': "Option 3"}
                ],
                'correctOption': "A"  # Placeholder, update with actual correct answer if available
            },
            'userContext': row['user_context']
        }

        return jsonify(session_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
