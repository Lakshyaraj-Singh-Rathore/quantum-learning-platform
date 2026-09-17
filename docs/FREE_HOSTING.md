# Free hosting for QuantumLearn

All memory figures below were measured on this codebase, not estimated.

## Why an earlier assessment said "not possible"

The first measurement loaded Qiskit, Aer, Cirq and PennyLane eagerly and came
to 406 MB, which does not fit Render's 512 MB free web service once Python,
uvicorn and a request are also in play.

That measurement was misleading. The heavy simulators are imported lazily
inside `run()`, so they are **not** resident until someone actually runs a
circuit on them:

| Stage | Peak RSS |
| --- | --- |
| API imported, idle | **155 MB** |
| after a Qiskit Aer run | 194 MB |
| after a Cirq run | 367 MB |
| after a PennyLane run | 429 MB |
| after a 20-qubit Aer run | 655 MB |

Two things follow. The API fits comfortably in 512 MB at idle and for Aer
work, and the real risk is not the framework set but **circuit size** — one
20-qubit circuit costs more than all three simulators combined.

## Recommended free split

Three providers, each doing the thing it is free at.

| Component | Host | Free allowance |
| --- | --- | --- |
| Streamlit UI | Streamlit Community Cloud | ~1 GB RAM, public repo |
| FastAPI backend | Render web service | 512 MB, 0.1 CPU, sleeps after 15 min |
| Postgres + pgvector | Neon or Supabase | no 30-day expiry |

The UI measures **151 MB** and never imports a simulator
(`qiskit`/`cirq`/`qiskit_aer` are all absent from `sys.modules` after loading
`lib.viz`, `lib.api_client` and `lib.composer`), so it sits well inside
Streamlit Cloud's 1 GB.

### Do not use Render's free Postgres

It is deleted 30 days after creation. Neon and Supabase both have a free
Postgres with pgvector and no expiry clock, which matters if this needs to
still work at a demo months from now.

## Running without Celery

Render's free tier has no background worker type. The app already supports
this: with `CELERY_TASK_ALWAYS_EAGER=true` the job runs inline in the API
process. Verified end to end with no Redis running at all:

```
API booted (no redis)      158 MB
job ran WITHOUT a worker   status=completed counts={'00': 132, '11': 124}
peak after simulation      201 MB
```

The cost is that a simulation blocks the request until it finishes. With the
8 s soft limit that is acceptable for a demo, and it removes both the worker
and Redis from the deployment.

## Required environment variables

Set on the Render service:

```
DATABASE_URL=<neon or supabase connection string>
CELERY_TASK_ALWAYS_EAGER=true
MAX_STATIC_QUBITS=14
GEMINI_API_KEY=<key>
QBRAID_API_KEY=<key>
```

`MAX_STATIC_QUBITS=14` is the important one. The default is 20, which peaks at
655 MB and would be OOM-killed on a 512 MB instance. At 14 qubits the
statevector is 0.26 MB and the peak stays near 200 MB. It is read from the
environment, so no code change is needed:

```
MAX_STATIC_QUBITS=14 -> 14
```

Oversized circuits are refused with HTTP 422 and an explanatory message rather
than taking the instance down.

On Streamlit Community Cloud set `API_BASE_URL` to the Render URL.

## Honest limitations

These are real and worth stating plainly rather than discovering during a
demo.

- **Cold start.** The Render service sleeps after 15 idle minutes and takes
  roughly a minute to wake. The first visitor after a quiet period waits.
- **0.1 CPU.** Simulations are much slower than on a laptop. Cirq and
  PennyLane in particular may approach the 8 s soft limit.
- **14-qubit ceiling** on the hosted instance, against 20 locally.
- **Ephemeral filesystem.** Anything written to disk is lost on restart;
  all state must live in Postgres.
- **750 instance hours per month** across the workspace, which is about one
  service running continuously.

## If the free tier proves too tight

The cheapest fix is Render's $7/month Starter: same 512 MB but no sleep and no
hour cap. $25/month buys 2 GB and 1 CPU, which would lift the qubit ceiling
back to 20 and make the multi-framework comparison feel responsive.
