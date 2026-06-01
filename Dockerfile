FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for aiohttp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY data/ ./data/

# Create directories for downloads and logs
RUN mkdir -p /app/downloads /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VIDEO_DOWNLOAD_DIR=/app/downloads
ENV LOG_DIR=/app/logs
ENV DB_PATH=/app/data/bot_history.db

# Run the bot
CMD ["python", "-m", "src.main"]
