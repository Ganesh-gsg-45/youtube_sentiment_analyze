FROM python:3.10-slim

# Install system dependencies
RUN apt-get update &amp;&amp; apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    &amp;&amp; rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY setup.py .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip &amp;&amp; \
    pip install --no-cache-dir -r requirements.txt &amp;&amp; \
    pip install --no-cache-dir -e .

# Download NLTK data
RUN python -c "import nltk; nltk.download('stopwords', quiet=True); nltk.download('punkt', quiet=True); nltk.download('wordnet', quiet=True); nltk.download('omw-1.4', quiet=True)"

# Create necessary directories
RUN mkdir -p models data/processed data/raw reports mlruns static/css static/js templates static/css templates/js

# Copy application code &amp; assets
COPY app.py .
COPY src/ ./src/
COPY static/ ./static/
COPY templates/ ./templates/
COPY params.yaml .
COPY models/ ./models/
COPY data/processed/ ./data/processed/

# Create non-root user
RUN groupadd -r appuser &amp;&amp; useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port (HF Spaces uses 7860)
EXPOSE 7860

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Run Flask app
CMD ["python", "app.py"]

