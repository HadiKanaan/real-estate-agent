# Use a small official Python 3.11 base image to keep image size reasonable while matching project requirements.
FROM python:3.11-slim

# Set the working directory inside the container so all subsequent commands run from /app.
WORKDIR /app

# Install curl for healthchecks and other utility tools; this is in the slim image base.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first so Docker can cache the install layer when app code changes.
COPY requirements.txt .

# Install Python dependencies without pip cache to reduce final image size and keep layers clean.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application code, including serialized model artifacts under app/model/.
COPY app ./app

# Expose port 8000 so the container documents the API port used by uvicorn.
EXPOSE 8000

# Health check: curl the /health endpoint to verify the API is responsive.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start uvicorn bound to 0.0.0.0 so host-to-container port mapping works correctly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
