# ==============================================================================
# Personal Brand Autonomous Agent — Google Cloud Run Serverless Webhook
# Scales to ZERO ($0 cost) when idle. Wakes up instantly on Telegram triggers.
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install system libraries for Pillow image rasterization, fonts, and audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-liberation \
    fonts-dejavu-core \
    ffmpeg \
    libfreetype6-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications first
COPY Personal_Brand/requirements.txt /app/requirements.txt

# Install lightweight CPU PyTorch wheel followed by Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.txt

# Pre-cache Whisper-tiny speech model into the Docker image layer
# This avoids downloading 150MB from HuggingFace on Cloud Run cold-starts!
RUN python -c "from transformers import pipeline; pipeline('automatic-speech-recognition', model='openai/whisper-tiny')"

# Copy the Personal_Brand package
COPY Personal_Brand /app/Personal_Brand

# Ensure directory structure for outputs and assets exists with correct permissions
RUN mkdir -p /app/Personal_Brand/output /app/Personal_Brand/assets && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

# Launch Uvicorn bound to Cloud Run dynamic $PORT with 1 lightweight worker
CMD ["sh", "-c", "exec uvicorn Personal_Brand.webhook_server:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
