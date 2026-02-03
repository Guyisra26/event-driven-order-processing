FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY libs/ ./libs/
COPY services/ ./services/

# Set Python path
ENV PYTHONPATH=/app

EXPOSE 8000
EXPOSE 8001
