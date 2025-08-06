# Backend Dockerfile for IP Expert project
# Multi-stage not required (small project). Use slim image for minimal size.

FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps required for building some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (leverages docker layer cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip cache purge

# Copy project source
COPY . .

# Expose Flask port
EXPOSE 5001

# Default command (can be overridden by docker-compose)
CMD ["python", "run.py"]
