#!/usr/bin/env bash
#
# PostgreSQL staging gate for the curriculum/mastery migration.
#
# Runs the real Alembic upgrade -> downgrade -> upgrade cycle against a
# DISPOSABLE PostgreSQL database and verifies the curriculum graph survives.
#
# This is NOT a production migration. Nothing here touches production.
# Production migration is a separate, explicit approval gate.
#
# Why pgserver: it ships PostgreSQL binaries as a wheel, so a real server can be
# started on machines without root and without Docker. The server binds to
# loopback only and every database is timestamp-named and disposable.
#
# Usage:
#   backend/scripts/pg_staging_check.sh
#
# Requirements: a Python environment with the backend requirements plus
#   `psycopg[binary]` and `pgserver`.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$REPO_ROOT/backend"

PG_VENV="${PG_VENV:-$HOME/.venv-pgstaging}"
PGDATA="${PGDATA:-/tmp/pgdata_staging_$$}"
PGPORT="${PGPORT:-5433}"

# Interpreter that has the backend requirements. Override to point at your own.
PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for cand in "$HOME/.venv-ql/bin/python" "python3" "python"; do
    if command -v "$cand" >/dev/null 2>&1; then PYTHON="$cand"; break; fi
  done
fi
echo "  python: $PYTHON"

echo "=== PostgreSQL staging gate ==="
echo "  repo:  $REPO_ROOT"
echo "  pgdata: $PGDATA (disposable)"
echo "  port:   $PGPORT (loopback only)"

# --- 1. environment --------------------------------------------------------- #
if [ ! -x "$PG_VENV/bin/python" ]; then
  echo "  creating venv: $PG_VENV"
  python3 -m venv "$PG_VENV"
  "$PG_VENV/bin/pip" install -q pgserver
fi
PGBIN="$("$PG_VENV/bin/python" -c "import pgserver,os;print(os.path.join(os.path.dirname(pgserver.__file__),'pginstall','bin'))")"
echo "  bundled binaries: $PGBIN"

# Driver for the application env.
if ! "$PYTHON" -c "import psycopg" 2>/dev/null; then
  echo "  installing psycopg into $PYTHON"
  "$PYTHON" -m pip install -q "psycopg[binary]"
fi

# --- 2. start a disposable server ------------------------------------------- #
if [ ! -d "$PGDATA" ]; then
  # UTF8 + C locale matter: without them some builds report the server version
  # as bytes and SQLAlchemy's postgres dialect raises
  # "cannot use a string pattern on a bytes-like object".
  "$PGBIN/initdb" -D "$PGDATA" -U postgres --auth=trust \
    --encoding=UTF8 --locale=C >/dev/null
fi
cat >> "$PGDATA/postgresql.conf" <<EOF
listen_addresses = '127.0.0.1'
port = $PGPORT
unix_socket_directories = '/tmp'
EOF
"$PGBIN/pg_ctl" -D "$PGDATA" -l "$PGDATA/server.log" -o "-c fsync=off" start >/dev/null 2>&1 || true
for _ in $(seq 1 30); do "$PGBIN/pg_isready" -h 127.0.0.1 -p "$PGPORT" >/dev/null && break; sleep 1; done
"$PGBIN/pg_isready" -h 127.0.0.1 -p "$PGPORT"
"$PGBIN/psql" -h 127.0.0.1 -p "$PGPORT" -U postgres -d postgres -tAc "SELECT version();" | head -1

STAGING_DB="ql_staging_$(date +%s)"
"$PGBIN/createdb" -h 127.0.0.1 -p "$PGPORT" -U postgres "$STAGING_DB"
echo "  staging database: $STAGING_DB"

# --- 3. run the real migration chain ---------------------------------------- #
cd "$BACKEND"
export DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:$PGPORT/$STAGING_DB"
export JWT_SECRET="${JWT_SECRET:-pg-staging-secret-not-for-production}"
export GEMINI_API_KEY="" QBRAID_API_KEY=""
export CONTENT_DIR="$REPO_ROOT/content"

# Seed legacy data at the pre-curriculum revision, because the curriculum
# migration attaches placements by scanning the lessons table.
"$PYTHON" -m alembic upgrade e9c4a7d31b22
"$PYTHON" - "$REPO_ROOT" <<'SEED'
import json, pathlib, sys, os
from sqlalchemy import create_engine, text
repo = sys.argv[1]
e = create_engine(os.environ["DATABASE_URL"])
slugs = sorted(p.stem for p in (pathlib.Path(repo) / "content").glob("*.md"))
with e.begin() as c:
    for s in slugs:
        c.execute(text("INSERT INTO lessons (slug,title,path,tags,order_index,track)"
                       " VALUES (:s,:t,:p,CAST(:tags AS jsonb),0,'theory')"),
                  {"s": s, "t": s, "p": f"{repo}/content/{s}.md", "tags": json.dumps([])})
    # user_mastery has a real FK to users, so the learner must exist first.
    c.execute(text("INSERT INTO users (email,password_hash,display_name,role,"
                   " is_active,created_at) VALUES ('legacy@staging.test',"
                   " 'not-a-real-login','Legacy Learner','student',true,"
                   " CURRENT_TIMESTAMP)"))
    uid = c.execute(text("SELECT id FROM users WHERE email='legacy@staging.test'")).scalar()
    for tag, score, att in [("noise",0.6,2),("decoherence",0.4,3),("grover",0.9,1),
                            ("algorithms",0.7,4),("qubit",0.8,3),("gates",0.5,2),
                            ("obsolete-tag",0.85,4)]:
        c.execute(text("INSERT INTO user_mastery (user_id,tag,score,attempts)"
                       " VALUES (:u,:t,:s,:a)"), {"u":uid,"t":tag,"s":score,"a":att})
print(f"  seeded {len(slugs)} lessons and 7 legacy mastery rows")
SEED

echo "  --- upgrade ---"
"$PYTHON" -m alembic upgrade head
"$PYTHON" -m alembic current | tail -1

"$PYTHON" - <<'VERIFY_BEFORE'
import os, json
from sqlalchemy import create_engine, text
e = create_engine(os.environ["DATABASE_URL"])
rows = sorted((r[0], r[1], bool(r[2])) for r in e.connect().execute(
    text("SELECT lesson_slug, topic_id, is_primary FROM lesson_topics")))
json.dump(rows, open("/tmp/pg_staging_graph.json", "w"))
print(f"  captured graph: {len(rows)} placements")
VERIFY_BEFORE

echo "  --- downgrade ---"
"$PYTHON" -m alembic downgrade f1a2b3c4d5e6
"$PYTHON" - <<'VERIFY_DOWN'
import os
from sqlalchemy import create_engine, text
e = create_engine(os.environ["DATABASE_URL"])
q = lambda s: e.connect().execute(text(s)).scalar()
total = q("SELECT count(*) FROM lessons")
placed = q("SELECT count(*) FROM lessons WHERE topic_slug IS NOT NULL")
extra = q("SELECT count(*) FROM lessons WHERE additional_topics IS NOT NULL")
print(f"  lessons placed on downgrade: {placed}/{total}")
print(f"  lessons carrying secondary placements: {extra}")
VERIFY_DOWN

echo "  --- re-upgrade ---"
"$PYTHON" -m alembic upgrade head

"$PYTHON" - <<'VERIFY_AFTER'
import os, json
from sqlalchemy import create_engine, text
e = create_engine(os.environ["DATABASE_URL"])
q = lambda s: e.connect().execute(text(s)).scalar()
before = {tuple(x) for x in json.load(open("/tmp/pg_staging_graph.json"))}
after = {(r[0], r[1], bool(r[2])) for r in e.connect().execute(
    text("SELECT lesson_slug, topic_id, is_primary FROM lesson_topics"))}
print(f"  lessons:    {q('SELECT count(DISTINCT lesson_slug) FROM lesson_topics')}/13")
print(f"  placements: {len(after)}/24")
print(f"  topics:     {q('SELECT count(*) FROM curriculum_topics')}/17")
print(f"  sections:   {q('SELECT count(*) FROM curriculum_sections')}/10")
print(f"  legacy mastery rows: {q('SELECT count(*) FROM user_mastery')}/7")
print(f"  derived mastery rows: {q('SELECT count(*) FROM topic_mastery')}/4")
print(f"  graph identical after round-trip: {before == after}")
if before != after:
    print("    missing:", sorted(before - after))
    print("    added:  ", sorted(after - before))
    raise SystemExit(1)
VERIFY_AFTER

echo
echo "=== PostgreSQL staging gate PASSED ==="
echo "  database $STAGING_DB left running on 127.0.0.1:$PGPORT for inspection"
echo "  stop with: $PGBIN/pg_ctl -D $PGDATA -m fast stop"
