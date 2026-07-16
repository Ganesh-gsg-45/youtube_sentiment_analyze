FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download NLTK data to the container-local NLTK_DATA directory
RUN python -c "import os; os.environ.setdefault('NLTK_DATA', '/app/nltk_data'); import nltk; nltk.download('stopwords', download_dir=os.environ['NLTK_DATA'], quiet=True); nltk.download('punkt', download_dir=os.environ['NLTK_DATA'], quiet=True); nltk.download('wordnet', download_dir=os.environ['NLTK_DATA'], quiet=True); nltk.download('omw-1.4', download_dir=os.environ['NLTK_DATA'], quiet=True)"

# Create necessary directories
RUN mkdir -p models data/processed data/raw reports mlruns static/css static/js templates static/css templates/js

# Copy application code & assets
COPY app.py .
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/
COPY params.yaml .
COPY models/ ./models/
COPY data/processed/ ./data/processed/

# Create non-root user with a valid home directory and local NLTK data storage
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser -s /usr/sbin/nologin appuser
ENV HOME=/home/appuser
ENV NLTK_DATA=/app/nltk_data
RUN mkdir -p /app/nltk_data /home/appuser && chown -R appuser:appuser /app /app/nltk_data /home/appuser
USER appuser

# Expose port (HF Spaces uses 7860)
EXPOSE 7860

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Run Flask app with Gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:7860", "--workers=1", "--threads=4", "--timeout=120", "app:app"]

