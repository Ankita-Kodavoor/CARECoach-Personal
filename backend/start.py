import os
import uvicorn

port = int(os.getenv("PORT", "5000"))  # Ensure PORT is converted to an integer

uvicorn.run("backend.websocket_server:app", host="0.0.0.0", port=port)
