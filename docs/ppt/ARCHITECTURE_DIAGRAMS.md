# Architecture Diagrams

All diagrams are derived from the code as it stands, not from intent. Route and
table counts were measured by importing the app and walking its routes/models.

---

## 1. System architecture

```mermaid
flowchart TB
    subgraph Browser["Browser — React 18 + TypeScript SPA (Vite)"]
        UI["Pages<br/>/learn · /curriculum · /composer<br/>/challenges · /codelab · /dashboard<br/>/games · /playground"]
        GRID["Shared composer grid<br/>frontend/circuit_composer/frontend/src<br/>compiled in via @composer alias"]
        UI --> GRID
    end

    UI -->|"fetch /api/* (same-origin)"| PROXY

    subgraph Serve["Serving"]
        PROXY["nginx (container)<br/>or Vite dev proxy<br/>strips the /api prefix"]
    end

    PROXY --> API

    subgraph Backend["FastAPI — 45 registered routes"]
        API["api/router.py"]
        API --> R1["auth (JWT)"]
        API --> R2["jobs (Celery)"]
        API --> R3["circuits (CRUD, QASM3,<br/>export, inspect, timeline)"]
        API --> R4["curriculum (topics,<br/>lessons, mastery)"]
        API --> R5["assessments (quizzes,<br/>challenges, games)"]
        API --> R6["ai (chat, generate)"]
        API --> R7["dashboard"]
    end

    R2 --> REDIS[("Redis<br/>broker + result backend")]
    R2 --> WORKER["Celery worker<br/>soft 8s / hard 15s"]

    R3 --> QS
    R4 --> DB
    R5 --> DB
    R6 --> AI

    subgraph QS["Quantum subsystem — backend/app/quantum"]
        IR["ir.py — CircuitIR (Pydantic)<br/>17 gates + if/for/while/box"]
        IR --> B1["qiskit_aer ✅"]
        IR --> B2["cirq ✅"]
        IR --> B3["pennylane ✅"]
        IR --> B4["dynamic_qiskit ✅"]
        IR --> B5["cudaq ⚠ needs GPU"]
        IR --> B6["qbraid 🔒 needs key"]
        NOISE["noise.py<br/>T1/T2/readout → Aer<br/>thermal_relaxation_error"]
        NOISE --> B1
        NOISE --> B5
        CODEGEN["codegen_qiskit / cirq /<br/>pennylane / qbraid"]
        IR --> CODEGEN
    end

    subgraph AI["AI / RAG"]
        GEM["gemini_client.py<br/>embed + chat"]
        RAG["rag.py — pgvector retrieval<br/>heading-aware chunking<br/>keyword fallback"]
        GEM --> RAG
    end

    subgraph Data["PostgreSQL + pgvector — 20 tables"]
        DB[("curriculum_topics · lessons<br/>content_chunks · topic_mastery<br/>simulation_jobs · challenge_attempts<br/>quiz_attempts · …")]
    end

    RAG --> DB

    style B1 fill:#d4edda
    style B2 fill:#d4edda
    style B3 fill:#d4edda
    style B4 fill:#d4edda
    style B5 fill:#fff3cd
    style B6 fill:#f8d7da
```

✅ runs with no credentials · ⚠ needs a GPU · 🔒 needs a paid key

---

## 2. Simulation request flow

```mermaid
sequenceDiagram
    participant S as Student
    participant UI as ComposerPage
    participant API as POST /jobs
    participant W as Celery worker
    participant Q as Backend adapter
    participant DB as Postgres

    S->>UI: build circuit on the grid
    UI->>UI: optional noise panel (T1/T2/readout)
    UI->>API: POST /jobs {ir, backend, shots, noise}
    API->>API: validate IR (Pydantic)
    API->>API: inspect_circuit() — qubit/shot limits
    API->>DB: INSERT simulation_jobs (queued)
    API-->>UI: 202 {job_id}

    alt Celery available
        API->>W: enqueue
    else CELERY_TASK_ALWAYS_EAGER
        API->>W: run inline in the request
    end

    W->>Q: run(ir, shots, seed, noise)
    Note over Q: guard_static_size() first<br/>noise model built only if enabled
    Q-->>W: {counts, probabilities, statevector, meta}
    W->>DB: UPDATE job (completed + result)

    loop every 500 ms until settled
        UI->>API: GET /jobs/{job_id}
    end

    UI->>API: GET /jobs/{job_id}/result
    API-->>UI: counts + probabilities + statevector
    UI->>UI: render histogram, Bloch, density matrix,
    UI->>UI: …and "noisy minus ideal" when noise is on
```

**Where the run hash matters:** `test_noise_model.py::test_run_hash_separates_noisy_from_ideal_runs`
ensures a noisy run never shares a cache entry with an ideal one.

---

## 3. RAG pipeline

```mermaid
flowchart LR
    A["content/*.md<br/>67 lessons<br/>153,324 words"] --> B["chunk_markdown()"]
    B --> C["split_on_headings()<br/>structure first"]
    C --> D["pack to<br/>CHUNK_TARGET_CHARS = 1200"]
    D --> E[("content_chunks<br/>+ pgvector embedding")]

    Q["Student question"] --> R{"GEMINI_API_KEY set?"}
    R -->|yes| V["embed → vector search"]
    R -->|no| K["keyword scoring<br/>(graceful fallback)"]
    V --> M["top-k chunks"]
    K --> M
    M --> G["Gemini: answer + citations"]
    G --> O["Grounded response"]

    E -.-> V
    E -.-> K

    H["Self-healing"] -.-> E
    H --> H1["re-chunk when the stored<br/>split no longer matches"]
    H --> H2["backfill embedding = NULL<br/>so RAG never degrades silently"]
```

Measured: `content/01_qubits.md` (13,497 chars) → **14 chunks**.

---

## 4. Learning workflow

```mermaid
flowchart TB
    S["Student signs in<br/>POST /auth/login → JWT"] --> C["GET /curriculum"]

    C --> TOPICS["71 topics<br/>17 published + 54 draft in the registry<br/>all 71 published in the DB"]

    TOPICS --> PREREQ{"evaluate_prerequisites()"}
    PREREQ -->|"prereqs unmet"| LOCK["locked — missing_required listed"]
    PREREQ -->|"prereqs met"| READY["ready"]

    READY --> LESSON["Read lesson<br/>67 markdown files<br/>344 cross-lesson links"]
    LESSON --> DEMO["Interactive demos<br/>golden-pinned to numpy"]
    LESSON --> TUTOR["AI tutor — RAG-cited"]

    DEMO --> BUILD["Composer: build a circuit"]
    BUILD --> RUN["Run on one of 6 backends"]
    RUN --> NOISE{"noise enabled?"}
    NOISE -->|yes| CMP["ideal vs noisy comparison"]
    NOISE -->|no| VIEW["histogram · Bloch · density matrix"]

    VIEW --> ASSESS["Quiz / challenge / game"]
    CMP --> ASSESS
    ASSESS --> AUTO["autograder<br/>PASS_THRESHOLD 0.8 (challenge)<br/>GAME_PASS_THRESHOLD 1.0 (game)"]

    AUTO --> MASTERY[("topic_mastery")]
    MASTERY --> DASH["Learner dashboard +<br/>instructor view + recommendations"]
    DASH --> TOPICS
```

---

## 5. Circuit IR object model

```mermaid
classDiagram
    class CircuitIR {
        +int n_qubits
        +list~Op~ ops
        +str name
        +has_measurements()
    }
    class Op {
        +str kind  %% gate | measure | reset | barrier | if | for | while | box
        +str gate
        +list~int~ qubits
        +list~int~ clbits
        +list~int~ controls
        +list~Param~ params
        +Condition condition
        +list~Op~ body
    }
    class Param {
        +str name
        +float value
    }
    class Condition {
        +str kind
        +list~int~ clbits
        +int value
    }
    CircuitIR "1" *-- "many" Op
    Op "1" *-- "many" Param
    Op "1" *-- "0..1" Condition
    Op "1" *-- "0..many" Op : nested body (control flow)
```

Gate set (17): `h x y z id swap s sdg t tdg sx p rx ry rz`
Controlled aliases: `cx/cnot`, `ccx/toffoli`, `mcx` (arbitrary controls), `cz`,
`cy`, `cp`, `crz`, `cswap/fredkin`.
Control flow: `if`, `for`, `while`, `box` — with `WHILE_CAP = 32`,
`FOR_LOOP_CAP = 1024`.

---

## 6. Deployment topology

```mermaid
flowchart LR
    subgraph Local["Local — make up"]
        DC["docker compose"]
        DC --> PG["postgres<br/>(pgvector)"]
        DC --> RD["redis"]
        DC --> AP["api<br/>:8000"]
        DC --> WK["worker<br/>(Celery)"]
        DC --> WB["web<br/>nginx :3000"]
    end

    subgraph Prod["Production — free tier"]
        RN["Render<br/>FastAPI, rootDir: backend<br/>512 MB, MAX_STATIC_QUBITS=14<br/>CELERY_TASK_ALWAYS_EAGER=true"]
        NB["Neon / Supabase<br/>Postgres + pgvector<br/>no 30-day expiry"]
        SH["Static host or container<br/>serves the SPA bundle"]
    end

    WB -.->|"/api proxy,<br/>same origin"| AP
    SH -.->|"if static: set VITE_API_BASE<br/>at BUILD time + API_CORS_ORIGINS"| RN
    RN --- NB

    NOTE["No CI exists.<br/>Tests run manually."]
```

**Note:** `VITE_API_BASE` is compiled in at build time — changing the API URL
requires a rebuild, not a config edit. If you serve the bundle behind an nginx
that proxies `/api`, leave it unset and CORS never enters the picture.
