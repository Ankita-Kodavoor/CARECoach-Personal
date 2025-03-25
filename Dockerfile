# Python application with FastAPI
FROM python:3.9-slim
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create data directory with appropriate permissions
RUN mkdir -p /data && chmod 777 /data

# Set environment variables
ENV DB_PATH=/data/test_input_v3.db
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Add empty __init__.py if it doesn't exist
RUN if [ ! -f /app/backend/__init__.py ]; then echo "# Package init" > /app/backend/__init__.py; fi

# Expose the port
EXPOSE 5000

# Use shell form to allow variable substitution
CMD python -m uvicorn backend.websocket_server:app --host 0.0.0.0 --port ${PORT:-5000}