# Autonomous Instagram Campaign Agent System (Google ADK 2.0)
# Containerized for Google Cloud Run deployment
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered standard I/O
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install required system packages for Pillow font rendering and SSL root certs
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu-core \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies into Python environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY instagram_adk /app/instagram_adk

# Create output media directory and configure permissions
RUN mkdir -p /app/instagram_adk/output

# Run as non-root user for security best practices
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose default Cloud Run container port
EXPOSE 8080

# Launch Uvicorn server bound to $PORT dynamically allocated by Google Cloud Run
CMD ["sh", "-c", "exec uvicorn instagram_adk.server:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
