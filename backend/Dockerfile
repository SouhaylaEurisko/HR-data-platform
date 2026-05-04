FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies for psycopg2 and PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the backend port
EXPOSE 4533

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4533"]
