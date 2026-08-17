FROM python:3.11-slim

# Install ffmpeg for video processing
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the FastAPI server by default
CMD ["uvicorn", "ai_faceless.api:app", "--host", "0.0.0.0", "--port", "8000"]