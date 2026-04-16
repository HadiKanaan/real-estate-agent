# Use a small official Python 3.11 base image to keep image size reasonable while matching project requirements.
FROM python:3.11-slim

# Set the working directory inside the container so all subsequent commands run from /app.
WORKDIR /app

# Copy dependency manifest first so Docker can cache the install layer when app code changes.
COPY requirements.txt .

# Install Python dependencies without pip cache to reduce final image size and keep layers clean.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application code, including serialized model artifacts under app/model/.
COPY app ./app

# Expose port 8000 so the container documents the API port used by uvicorn.
EXPOSE 8000

# Start uvicorn bound to 0.0.0.0 so host-to-container port mapping works correctly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
