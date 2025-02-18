from flask import Flask, jsonify
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

        # Fetch only the required fields from practice_session
        cursor.execute("""
            SELECT 
                practicesession_id, user_id, chat_code, target_skill, target_utterance_id, 
                utterance_feedback, utterance_alternative, user_context, target_subskill
            FROM practice_session
            WHERE chat_code = ?
        """, (chat_code,))
        
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({'error': 'Chat code not found in practice_session'}), 404

        # Prepare JSON response with ONLY the requested fields
        session_data = {
            'practiceSessionId': row['practicesession_id'],
            'userId': row['user_id'],
            'chatCode': row['chat_code'],
            'targetSkill': row['target_skill'],
            'targetUtteranceId': row['target_utterance_id'],
            'utteranceFeedback': row['utterance_feedback'],
            'utteranceAlternative': row['utterance_alternative'],
            'userContext': row['user_context'],
            'targetSubskill': row['target_subskill']
        }

        return jsonify(session_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)


