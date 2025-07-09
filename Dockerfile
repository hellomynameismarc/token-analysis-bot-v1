# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

# Prevent interactive prompts & set up env vars
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install build dependencies (optional, kept minimal for slim image)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (leverages Docker layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Default command (can be overridden)
CMD ["python", "-m", "bot.main"] 