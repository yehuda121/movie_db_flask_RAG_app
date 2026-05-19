FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Folders used at runtime (DB and uploads are mounted via docker-compose volumes)
RUN mkdir -p data/faiss data/models static/images/posters static/css

ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "app.py"]
