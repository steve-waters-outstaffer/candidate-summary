FROM python:3.11-slim

# Install system dependencies for python-magic and build tools for pycairo
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libmagic-dev \
    file \
    gcc \
    build-essential \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Run with gunicorn with optimized settings for long-running processes
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--worker-class", "sync", "--timeout", "3600", "--keep-alive", "2", "--max-requests", "100", "--max-requests-jitter", "10", "app:app"]