# Deploying QuantumLearn

Three free services, each doing the part it is actually free at.

| Part | Host | Why |
| --- | --- | --- |
| Streamlit UI | Streamlit Community Cloud | ~1 GB RAM, free, no card |
| FastAPI backend | Render (free web service) | 512 MB, Docker-free Python build |
| Postgres + pgvector | Neon (or Supabase) | free and does **not** expire |

Do **not** use Render's free Postgres: it is deleted 30 days after creation.
Neon and Supabase have no expiry clock.

Everything below was exercised locally with the production settings before
being written down.

---

## 1. Database (Neon)

1. Create a project at <https://neon.tech> and copy the connection string.
2. Enable pgvector once, from the Neon SQL editor:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. Keep the URL for the next step. It looks like:

   ```
   postgresql://user:password@ep-xxx.aws.neon.tech/neondb?sslmode=require
   ```

## 2. Backend (Render)

The repository already contains `render.yaml`, so Render can configure the
service itself.

1. Go to <https://dashboard.render.com> → **New** → **Blueprint**.
2. Point it at this repository and pick the branch.
3. Render reads `render.yaml` and creates **quantumlearn-api**.
4. Fill in the four secrets it asks for:

   | Variable | Value |
   | --- | --- |
   | `DATABASE_URL` | the Neon string from step 1 |
   | `JWT_SECRET` | any long random string |
   | `GEMINI_API_KEY` | your Gemini key |
   | `QBRAID_API_KEY` | your qBraid key |
   | `API_CORS_ORIGINS` | leave blank for now — step 4 fills it in |

5. Deploy, then check the health endpoint:

   ```
   https://quantumlearn-api.onrender.com/health   ->   {"status":"ok"}
   ```

`startCommand` runs `alembic upgrade head` before uvicorn, so the schema is
created on first boot. Verified locally: 15 tables.

### Settings that matter on a 512 MB box

`render.yaml` sets these already; they are listed so the reasoning is not lost.

- `CELERY_TASK_ALWAYS_EAGER=true` — the free tier has no worker type, so jobs
  run inline in the web process. Verified working with no Redis at all.
- `MAX_STATIC_QUBITS=14` — the default of 20 peaks at ~655 MB and would be
  OOM-killed. 14 keeps the peak near 200 MB. Oversized circuits get a clean
  HTTP 422 instead of taking the instance down.

## 3. Frontend (Streamlit Community Cloud)

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. **New app** → this repository → branch → main file `frontend/Home.py`.
3. Under **Advanced settings → Secrets**, add:

   ```toml
   API_BASE_URL = "https://quantumlearn-api.onrender.com"
   ```

4. Deploy. You get a URL like `https://<name>.streamlit.app`.

Community Cloud installs the root `requirements.txt`, which pulls in
`frontend/requirements.txt` only. The UI never imports qiskit, cirq or
pennylane — measured at **151 MB**, comfortably inside the 1 GB limit.

It does need `CircuitIR` from the backend package. Docker supplies that with
`PYTHONPATH=/backend`, which Community Cloud cannot set, so
`frontend/lib/bootstrap.py` puts `backend/` on `sys.path` itself. Verified with
`PYTHONPATH` unset.

## 4. Close the CORS loop

Go back to Render → **Environment** and set:

```
API_CORS_ORIGINS = https://<your-app>.streamlit.app
```

Save; Render restarts automatically. Until this is set the API allows `*`,
which works but is worth tightening. Verified locally: the allowed origin gets
`access-control-allow-origin` back, any other origin gets **400**.

## 5. Check it end to end

On the Streamlit URL: register an account, open **Composer**, build a Bell
pair, press **Run simulation**. You should get roughly 50/50 on `00` and `11`.

The same flow against a production-configured API locally:

```
register -> 201
lessons  -> 13
submit   -> 201
result   -> completed {'00': 251, '11': 261}
18 qubits (cap 14) -> 422
```

---

## Known limits of the free tier

State these rather than discover them during a demo.

- **Cold start.** The Render service sleeps after 15 idle minutes and takes
  about a minute to wake. **Open the URL a few minutes before presenting.**
- **0.1 CPU.** Simulations are much slower than on a laptop. Cirq and
  PennyLane can approach the 8 s soft limit.
- **14 qubits** hosted, against 20 locally.
- **qBraid will usually time out.** It waits on a remote queue that does not
  finish inside 8 s, and credits are spent at submission. Demonstrate qBraid
  once, then use Qiskit Aer, which is instant, free and identical for static
  circuits.
- **Ephemeral disk.** All state must live in Postgres.
- **750 instance hours/month**, about one service running continuously.

## If the free tier is too tight

Render Starter at $7/month removes the sleep and the hour cap at the same
512 MB. $25/month gives 2 GB and a full CPU, which would put the qubit ceiling
back to 20 and make the multi-framework comparison feel responsive.

## Keeping Docker for local work

`docker compose up -d --build` is unchanged and still the best way to run the
whole stack locally, including Redis and a real Celery worker.
