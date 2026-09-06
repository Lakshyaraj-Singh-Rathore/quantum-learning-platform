# ---------------------------------------------------------------- stage 1
# Build the React drag-and-drop circuit composer bundle.
FROM node:20-slim AS composer

WORKDIR /composer
COPY circuit_composer/frontend/package*.json ./
RUN npm ci
COPY circuit_composer/frontend/ ./
RUN npm run build

# ---------------------------------------------------------------- stage 2
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/backend

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Ship the compiled component; without it the app falls back to the
# pure-Python grid composer, which offers the same functionality.
COPY --from=composer /composer/build ./circuit_composer/frontend/build

EXPOSE 8501
CMD ["streamlit", "run", "Home.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
