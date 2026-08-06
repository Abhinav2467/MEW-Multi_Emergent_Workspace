FROM python:3.11-slim

WORKDIR /app

# System dependencies for compiling native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create persistent data directories
RUN mkdir -p backend/data backend/reports backend/data/resumes

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["python", "-m", "backend.main"]
