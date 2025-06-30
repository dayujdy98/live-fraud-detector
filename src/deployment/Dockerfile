# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy deployment requirements and install dependencies
COPY src/deployment/deployment_requirements.txt .
RUN pip install --no-cache-dir -r deployment_requirements.txt

# Copy the entire src directory
COPY src/ ./src/

# Create data directory for logging
RUN mkdir -p /app/data && chmod 755 /app/data

# Set environment variables
ENV PYTHONPATH="/app/src"
ENV MLFLOW_TRACKING_URI=""

# Expose port 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application with uvicorn
CMD ["uvicorn", "src.deployment.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
