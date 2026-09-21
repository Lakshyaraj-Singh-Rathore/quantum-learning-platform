# ---------------------------------------------------------------- stage 1
# Build the React drag-and-drop circuit composer bundle.
FROM node:20-slim AS composer

WORKDIR /composer
COPY circuit_composer/frontend/package*.json ./
RUN npm ci
COPY circuit_composer/frontend/ ./
RUN npm run build

# ---------------------------------------------------------------- stage 1b
# Build the continuous Bloch sphere bundle.
FROM node:20-slim AS bloch

WORKDIR /bloch
COPY live_bloch/frontend/package*.json ./
RUN npm install
COPY live_bloch/frontend/ ./
RUN npm run build

# ---------------------------------------------------------------- stage 2
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/backend

# media-types installs /etc/mime.types. Without it Python's mimetypes module
# falls back to "application/javascript" for .js, which some browsers refuse to
# execute as an ES module -- the drag-and-drop composer then renders as a blank
# white iframe with no console error.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential media-types && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Ship the compiled component; without it the app falls back to the
# pure-Python grid composer, which offers the same functionality.
COPY --from=composer /composer/build ./circuit_composer/frontend/build
# Same for the live Bloch sphere; without it the lessons fall back to the
# Plotly sphere, which is correct but reruns the page on every slider move.
COPY --from=bloch /bloch/build ./live_bloch/frontend/build

EXPOSE 8501
CMD ["streamlit", "run", "Home.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
