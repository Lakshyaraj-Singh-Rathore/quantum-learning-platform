FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# GPU images are opt-in: the cudaq wheel drags ~1.5 GB of CUDA runtimes, and
# a teaching deployment's default (CPU cloud) must not pay that. See
# docker-compose.gpu.yml.
ARG INSTALL_CUDAQ=false

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# After the base install so the pinned numpy<2 stack is already decided; the
# resolver keeps it (cudaq accepts numpy 1.26, verified on 3.11).
RUN if [ "$INSTALL_CUDAQ" = "true" ]; then pip install --no-cache-dir "cudaq==0.16.*"; fi

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
