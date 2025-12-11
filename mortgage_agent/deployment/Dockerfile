# UAE Mortgage Assistant
# Multi-stage build for optimized production image

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies globally
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder (global site-packages)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (only mortgage_agent needed for adk web)
COPY mortgage_agent/ ./mortgage_agent/

# Create non-root user for security and set permissions
RUN useradd --create-home appuser && chown -R appuser /app

# Environment variables (PORT will be overridden by Railway)
ENV HOST=0.0.0.0
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Health check for ADK web
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/')" || exit 1

# Expose port
EXPOSE 8000

# Run ADK web - bind to 0.0.0.0 for external access, use Railway's $PORT
CMD adk web --host 0.0.0.0 --port $PORT mortgage_agent
