# QuantumLearn — AI Interactive Quantum Algorithm Learning Platform

Streamlit + FastAPI + Celery + Postgres/pgvector + Gemini.

## Quick start

```bash
cp .env.example .env
# optional: GEMINI_API_KEY, QBRAID_API_KEY, QBRAID_DEVICE_ID
docker compose up --build
```

- UI: http://localhost:8501
- API: http://localhost:8000/docs

Bootstrap accounts:

- admin@local.dev / admin123
- instructor@local.dev / instructor123

Register a student from the UI.

```bash
make test
make seed
```

## Optional React composer

Python grid composer works out of the box. To enable the React drag-drop component:

```bash
cd frontend/circuit_composer/frontend
npm install
npm run build
```

## Local (no Docker)

Postgres 16 + pgvector, Redis, then:

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
celery -A app.workers.celery_app.celery_app worker -l info

cd frontend && pip install -r requirements.txt
PYTHONPATH=../backend API_BASE_URL=http://localhost:8000 streamlit run Home.py
```
