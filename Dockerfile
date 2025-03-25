# Single-stage build for simplicity
FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your code
COPY . .

# Create data directory
RUN mkdir -p /data && chmod 777 /data

# Set environment variables
ENV DB_PATH=/data/test_input_v3.db
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Debug - list files to verify structure
RUN echo "Files in backend directory:" && ls -la backend/

# Expose port
EXPOSE 5000

# Run from the root directory, using the module path
CMD ["uvicorn", "backend.websocket_server:app", "--host", "0.0.0.0", "--port", "${PORT:-5000}"]