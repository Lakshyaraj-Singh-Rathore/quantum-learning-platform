.PHONY: up down logs test seed

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api worker streamlit

test:
	docker compose exec api pytest -q

seed:
	docker compose exec api python -c "from app.database import SessionLocal; from app.seed import seed_all; s=SessionLocal(); seed_all(s); s.close()"