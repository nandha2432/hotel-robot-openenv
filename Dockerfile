# Dockerfile for Hotel Robot Delivery Environment
# HuggingFace Spaces requires port 7860

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy all project files into container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# HuggingFace Spaces requires port 7860
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]