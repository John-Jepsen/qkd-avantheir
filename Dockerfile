FROM python:3.11-slim

WORKDIR /app

# Install system deps for numpy/scikit-learn compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY implementation/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy implementation code
COPY implementation/ .

# Train models at build time so container starts fast
RUN python train_all_models.py

# Cloud Run sets $PORT; default to 8000 for local
ENV PORT=8000

EXPOSE ${PORT}

CMD uvicorn api:app --host 0.0.0.0 --port ${PORT}
