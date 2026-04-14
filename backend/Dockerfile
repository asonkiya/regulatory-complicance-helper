FROM python:3.11-slim

# System dependencies: tesseract, ffmpeg, poppler
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    ffmpeg \
    libpoppler-cpp-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Storage directory
RUN mkdir -p /app/storage

EXPOSE 8000
