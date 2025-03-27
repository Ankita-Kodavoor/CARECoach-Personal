import os
import sys
import json
import traceback
import inspect
import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from . import database
from . import config
from .response_scorer import score_and_update
from .freeform import get_freeform
# Import the module instead of individual functions
from . import subskill_manager

# Initialize the database using the database module
database.initialize_database()

# Define current_dir (for static files)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total connections: {len(self.active_connections)}", file=sys.stderr)

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected. Remaining connections: {len(self.active_connections)}", file=sys.stderr)
            
    async def send_message(self, client_id: str, message: str):
        if client_id in self.active_connections:
            formatted_timestamp = datetime.datetime.now().isoformat(timespec="seconds") + "Z"
            await self.active_connections[client_id].send_json({
                "message": message,
                "timestamp": formatted_timestamp
            })

# Initialize connection manager
manager = ConnectionManager()

@app.get('/api/session/{practicesession_id}/subskills')
async def get_session_subskills(practicesession_id: int):
    """API endpoint to get all subskills for a given practice session."""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Query the subskill_map table for unique subskills for this session
        cursor.execute("""
            SELECT DISTINCT subskill 
            FROM subskill_map
            WHERE practicesession_id = %s AND subskill IS NOT NULL
            ORDER BY subskill
        """, (practicesession_id,))
        
        subskills = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return {
            'success': True,
            'practicesession_id': practicesession_id,
            'subskills': subskills
        }
    except Exception as e:
        print(f"Error in get_session_subskills: {str(e)}", file=sys.stderr)
        return {
            'success': False,
            'error': str(e),
            'subskills': []
        }
    
# Helper function to safely handle get_freeform regardless of whether it's async or not
# First, update the safe_get_freeform function to handle the tuple return type
async def safe_get_freeform(user_id, chat_code):
    try:
        # Check if get_freeform is a coroutine function
        if inspect.iscoroutinefunction(get_freeform):
            # It's async, await it
            result = await get_freeform(user_id, chat_code)
            # Check if result is a tuple (message, should_force_next_subskill)
            if isinstance(result, tuple) and len(result) == 2:
                return result
            # If not a tuple, assume it's just the message with no force flag
            return result, False
        else:
            # It's not async
            result = get_freeform(user_id, chat_code)
            # Handle potential tuple return
            if isinstance(result, tuple) and len(result) == 2:
                return result
            return result, False
    except Exception as e:
        print(f"Error in safe_get_freeform: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "I'm here to help with your practice. How would you like to continue?", False

# Then create a similar safe function for get_next_subskill_message
async def safe_get_next_subskill_message(user_id, chat_code):
    try:
        # Import this function to avoid circular imports
        from .freeform import get_next_subskill_message
        
        # Check if the function is async
        if inspect.iscoroutinefunction(get_next_subskill_message):
            # It's async, await it
            return await get_next_subskill_message(user_id, chat_code)
        else:
            # It's not async
            return get_next_subskill_message(user_id, chat_code)
    except Exception as e:
        print(f"Error in safe_get_next_subskill_message: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return "Let's continue with the next skill."


# Basic health check endpoint
@app.get("/ping")
async def ping():
    return {"status": "alive", "timestamp": datetime.datetime.now().isoformat()}

# Debug route to check server config
@app.get("/api/debug")
async def debug_info():
    """Return debug information about the server configuration."""
    # Try to count sessions in database
    db_session_count = 0
    db_error = None
    db_url = os.environ.get('DATABASE_URL', 'Not available')
    
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM practice_session")
        db_session_count = cursor.fetchone()[0]
        conn.close()
    except Exception as e:
        db_error = str(e)
    
    return {
        "database_url": "PostgreSQL: ***" if db_url else "Not configured",
        "db_session_count": db_session_count,
        "db_error": db_error,
        "is_get_freeform_async": inspect.iscoroutinefunction(get_freeform)
    }

# API endpoint to get user sessions
@app.get("/api/user/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """Get all practice sessions for a given user ID from the database."""
    print(f"Fetching sessions for user_id: {user_id}", file=sys.stderr)
    error_msg = None
    sessions = []
    
    # Try database
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Try to query with user_id
        try:
            cursor.execute("""
                SELECT practicesession_id, chat_code, target_subskill 
                FROM practice_session
                WHERE user_id = %s
                ORDER BY practicesession_id DESC
            """, (user_id,))
                    
            for row in cursor.fetchall():
                practicesession_id, chat_code, target_subskill = row
                sessions.append({
                    "practicesession_id": practicesession_id,
                    "chat_code": chat_code,
                    "target_subskill": target_subskill,
                    "user_id": user_id
                })
        except Exception as e:
            error_msg = f"Error querying database: {str(e)}"
            
        conn.close()
        
        # If we found sessions, return them
        if sessions:
            print(f"Found {len(sessions)} sessions for user {user_id} in database", file=sys.stderr)
            return {"sessions": sessions}
                
    except Exception as e:
        error_msg = f"Database error: {str(e)}"
        traceback.print_exc(file=sys.stderr)
    
    # If we get here, no sessions were found
    print(f"No sessions found for user {user_id}", file=sys.stderr)
    if error_msg:
        return {"error": error_msg, "sessions": []}
    else:
        return {"sessions": []}
    
@app.get('/api/utterance-rewind/{practicesession_id}')
async def get_utterance_rewind_api(practicesession_id: int):
    """API endpoint to get utterance rewind for a given practice session."""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        # Directly query the utterance_rewind field from the practice_session table
        cursor.execute("""
            SELECT utterance_rewind
            FROM practice_session
            WHERE practicesession_id = %s
        """, (practicesession_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        utterance_rewind = result[0] if result and result[0] else ""
        
        return {
            'success': True,
            'practicesession_id': practicesession_id,
            'utteranceRewind': utterance_rewind
        }
    except Exception as e:
        print(f"Error in get_utterance_rewind_api: {str(e)}", file=sys.stderr)
        return {
            'success': False,
            'error': str(e),
            'utteranceRewind': ''
        }
@app.websocket("/ws/session/{practicesession_id}")
async def websocket_endpoint(websocket: WebSocket, practicesession_id: int):
    print(f"WebSocket connected with practicesession_id: {practicesession_id}", file=sys.stderr)
    client_id = f"client_{practicesession_id}_{datetime.datetime.now().timestamp()}"
    
    await manager.connect(websocket, client_id)
    
    try:
        # Default values in case we can't find the session
        user_id = "default_user"
        chat_code = f"mock-{practicesession_id}"
        
        # Get session from database
        try:
            conn = database.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, chat_code, current_state FROM practice_session WHERE practicesession_id = %s", 
                          (practicesession_id,))
                
            session_data = cursor.fetchone()
            conn.close()
            
            if session_data:
                user_id, chat_code, current_state = session_data
                print(f"Found session in DB: user_id={user_id}, chat_code={chat_code}, state={current_state}", file=sys.stderr)
                
                # If session is already in completed state, skip forcing next subskill
                if current_state == "completed":
                    print(f"Session {practicesession_id} is already in completed state", file=sys.stderr)
        except Exception as e:
            print(f"Error getting session from database: {str(e)}", file=sys.stderr)
        
        # Use fallback message if get_freeform doesn't work
        fallback_message = "Welcome to the chat! I'm here to help you practice your motivational interviewing skills."
        
        # Try to get initial message from get_freeform using our safe helper
        try:
            initial_message, should_force_next_subskill = await safe_get_freeform(user_id, chat_code)
            if not initial_message or (isinstance(initial_message, str) and initial_message.startswith("Error")):
                initial_message = fallback_message
                should_force_next_subskill = False
                
            # If the message contains completion text, don't force next subskill
            if "Congratulations on completing your learning session" in initial_message:
                should_force_next_subskill = False
                
            # Check if the session is now in completed state
            try:
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT current_state FROM practice_session WHERE practicesession_id = %s", 
                              (practicesession_id,))
                current_state = cursor.fetchone()[0]
                conn.close()
                
                if current_state == "completed":
                    should_force_next_subskill = False
            except Exception as db_error:
                print(f"Error checking session state: {db_error}", file=sys.stderr)
                
        except Exception as e:
            print(f"Error getting freeform message: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            initial_message = fallback_message
            should_force_next_subskill = False
        
        # Send initial message
        await manager.send_message(client_id, initial_message)
        
        # Check if we need to force next subskill message
        if should_force_next_subskill:
            # Small delay for natural feel
            import asyncio
            await asyncio.sleep(1.5)
            
            # Double-check that the session isn't in completed state
            try:
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT current_state FROM practice_session WHERE practicesession_id = %s", 
                              (practicesession_id,))
                current_state = cursor.fetchone()[0]
                conn.close()
                
                if current_state == "completed":
                    print(f"Session moved to completed state, skipping next subskill message", file=sys.stderr)
                    should_force_next_subskill = False
            except Exception as db_error:
                print(f"Error checking session state: {db_error}", file=sys.stderr)
            
            if should_force_next_subskill:
                # Get next subskill message
                next_message = await safe_get_next_subskill_message(user_id, chat_code)
                
                # Send second message with next subskill
                await manager.send_message(client_id, next_message)
        
        # Handle incoming messages
        while True:
            user_message = await websocket.receive_text()
            print(f"Received message from {client_id}: {user_message}", file=sys.stderr)
            
            # Try to store user message (ignore errors)
            try:
                # Connect to database
                conn = database.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO freeform_dialogue
                    (practicesession_id, user_id, utterance, role, state)
                    VALUES (%s, %s, %s, %s, %s)
                """, (practicesession_id, user_id, user_message, 'user', None))  
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Could not store message: {str(e)}", file=sys.stderr)
            
            # Try to get AI response using our safe helper
            try:
                response, should_force_next_subskill = await safe_get_freeform(user_id, chat_code)
                
                # Error handling for the response
                if not response or (isinstance(response, str) and response.startswith("Error")):
                    response = "I understand. Can you tell me more about that?"
                    should_force_next_subskill = False
                
                # If the message contains completion text, don't force next subskill
                if "Congratulations on completing your learning session" in response:
                    should_force_next_subskill = False
                    
                # Check if session is now in completed state
                try:
                    conn = database.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT current_state FROM practice_session WHERE practicesession_id = %s", 
                                  (practicesession_id,))
                    current_state = cursor.fetchone()[0]
                    conn.close()
                    
                    if current_state == "completed":
                        should_force_next_subskill = False
                except Exception as db_error:
                    print(f"Error checking session state: {db_error}", file=sys.stderr)
                
            except Exception as e:
                print(f"Error getting freeform response: {str(e)}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                response = "I understand. Can you tell me more about that?"
                should_force_next_subskill = False
        
            # Send response back to client
            await manager.send_message(client_id, response)
            
            # Check if we need to force next subskill message
            if should_force_next_subskill:
                # Small delay for natural feel
                import asyncio
                await asyncio.sleep(1.5)
                
                # Double-check that the session isn't in completed state
                try:
                    conn = database.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT current_state FROM practice_session WHERE practicesession_id = %s", 
                                  (practicesession_id,))
                    current_state = cursor.fetchone()[0]
                    conn.close()
                    
                    if current_state == "completed":
                        print(f"Session moved to completed state, skipping next subskill message", file=sys.stderr)
                        should_force_next_subskill = False
                except Exception as db_error:
                    print(f"Error checking session state: {db_error}", file=sys.stderr)
                
                if should_force_next_subskill:
                    # Get next subskill message
                    next_message = await safe_get_next_subskill_message(user_id, chat_code)
                    
                    # Send second message with next subskill
                    await manager.send_message(client_id, next_message)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected", file=sys.stderr)
    except Exception as e:
        print(f"Error in websocket: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        try:
            await manager.send_message(client_id, f"An error occurred. Please refresh the page to reconnect.")
        except:
            pass
        manager.disconnect(client_id)

@app.get('/api/session/{practicesession_id}/current-subskill')
async def get_current_subskill_api(practicesession_id: int):
    """API endpoint to get the current target subskill for a practice session."""
    try:
        # Import the function from subskill_manager
        # Import the module instead of individual functions
        

        # To this:
        current_subskill = subskill_manager.get_current_subskill(practicesession_id)
        # # Get the current subskill
        # current_subskill = get_current_subskill(practicesession_id)
        
        return {
            'success': True,
            'practicesession_id': practicesession_id,
            'target_subskill': current_subskill
        }
    except Exception as e:
        print(f"Error in get_current_subskill_api: {str(e)}", file=sys.stderr)
        return {
            'success': False,
            'error': str(e),
            'target_subskill': None
        }
    
# Add this to websocket_server.py
@app.get('/api/subskill-progress/{practicesession_id}')
async def get_subskill_progress_api(practicesession_id: int):
    """API endpoint to get subskill progress for a given practice session."""
    try:
        # Import the functions from subskill_manager
        # Import the module
        # from . import subskill_manager
        # from subskill_manager import get_subskill_progress, get_unique_subskills, get_current_subskill
        
        # Get the progress data
        progress = subskill_manager.get_subskill_progress(practicesession_id)

        # Get unique subskills with completion status
        unique_subskills = subskill_manager.get_unique_subskills(practicesession_id)

        # Get the current target subskill directly
        current_subskill = subskill_manager.get_current_subskill(practicesession_id)
        
        # Extract completed subskills
        completed_subskills = [s["subskill"] for s in unique_subskills if s["completed"]]
        
        # Extract the data we need
        total_count = progress.get('total', 0)
        remaining = progress.get('remaining', [])
        
        return {
            'success': True,
            'practicesession_id': practicesession_id,
            'subskillProgress': {
                'current': current_subskill,  # Changed to directly use the current subskill string
                'total': total_count,
                'completed': completed_subskills
            }
        }
    except Exception as e:
        print(f"Error in get_subskill_progress_api: {str(e)}", file=sys.stderr)
        return {
            'success': False,
            'error': str(e),
            'subskillProgress': {
                'current': None,
                'total': 0,
                'completed': []
            }
        }
        
# Run the server with dynamic port from environment
if __name__ == "__main__":    
    # If we have a public folder, mount it
    public_dir = os.path.join(current_dir, "public")
    if os.path.exists(public_dir) and os.path.isdir(public_dir):
        app.mount("/", StaticFiles(directory=public_dir), name="public")

    import os
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("backend.websocket_server:app", host="0.0.0.0", port=port, reload=True)

