# Frontend build stage
FROM node:18 AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source code and build
COPY frontend/ ./
RUN npm run build

# Backend stage
FROM python:3.9-alpine  
#Use alpine for a smaller image

WORKDIR /app

# Install Python dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache

# Copy frontend build
COPY --from=frontend-builder /app/frontend/build /app/public

# Copy backend code
COPY backend/ ./backend/

# Ensure database directory exists
RUN mkdir -p /data

# Set environment variables
ENV DB_PATH=/data/test_input_v3.db
ENV NODE_ENV=production

# Expose port (Railway sets this automatically)
EXPOSE 5000

# Start backend server
CMD uvicorn backend.websocket_server:app --host 0.0.0.0 --port ${PORT:-5000}
