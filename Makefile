# One entry point for every machine. The Compose GPU override (CUDA-Q baked
# into api/worker, container handed the card) is picked up AUTOMATICALLY
# whenever Docker can actually use a GPU -- so a student on a CPU laptop and
# an instructor on a GPU box both just run `make up` and get the right stack.
# Force either way: `make up GPU=1` / `make up GPU=0`.

GPU ?= auto

ifeq ($(GPU),auto)
GPU_FILES := $(shell docker run --rm --gpus all alpine true >/dev/null 2>&1 \
               && echo -f docker-compose.yml -f docker-compose.gpu.yml)
else ifeq ($(GPU),1)
GPU_FILES := -f docker-compose.yml -f docker-compose.gpu.yml
endif

COMPOSE := docker compose $(GPU_FILES)

.PHONY: up down logs test seed migrate revision composer gpu-check

gpu-check:
	@echo "$(if $(GPU_FILES),GPU mode: CUDA-Q will be available (up to 28 qubits),CPU mode: plain stack - Docker sees no usable NVIDIA GPU)"

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api worker streamlit

test:
	$(COMPOSE) exec api pytest -q

seed:
	$(COMPOSE) exec api python -c "from app.database import SessionLocal; from app.seed import seed_all; s=SessionLocal(); seed_all(s); s.close()"

migrate:
	$(COMPOSE) exec api alembic upgrade head

revision:
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

composer:
	cd frontend/circuit_composer/frontend && npm install && npm run build
