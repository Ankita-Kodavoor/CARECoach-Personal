FROM node:18 AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source code
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Use Python for the backend
FROM python:3.9-slim

WORKDIR /app

# Install Node.js and npm for serving the frontend
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend assets
COPY --from=frontend-builder /app/frontend/build /app/public

# Copy backend code - make sure it goes into a backend directory
COPY backend/ ./backend/

# Create a directory for the database
RUN mkdir -p /data

# Environment variables
ENV DB_PATH=/data/test_input_v3.db
ENV NODE_ENV=production

# Expose port (Railway will override this with its own PORT)
EXPOSE 8000

# Let Railway.json handle the start command
CMD uvicorn backend.websocket_server:app --host 0.0.0.0 --port ${PORT:-5000}