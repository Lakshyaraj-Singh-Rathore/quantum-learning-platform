#!/usr/bin/env bash
# Rebuild this workspace after a sandbox reset.
#
# A sandbox reset can move HEAD back to an older commit while leaving the
# working tree contents in place, or wipe the Python venv / node_modules that
# live OUTSIDE git. This script only ever restores things it can prove are
# already correct; it asks before doing anything that could discard work.
#
# Usage:  bash tools/recover.sh
set -uo pipefail

BRANCH="arena/01a0d874-quantum-learning-platform"
REMOTE="origin"
VENV="/home/user/.venv-ql"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO"

hr() { printf '%s\n' "------------------------------------------------------------"; }

hr
echo "Repository : $REPO"
echo "Branch     : $BRANCH"
echo "Local HEAD : $(git rev-parse --short HEAD 2>/dev/null || echo MISSING)"
echo "Venv       : ${VENV}$([ -d "$VENV" ] && echo ' (present)' || echo ' (MISSING)')"
echo "web/node_modules      : $([ -d frontend/web/node_modules ] && echo present || echo MISSING)"
echo "frontend/node_modules : $([ -d frontend/node_modules ] && echo present || echo MISSING)"
hr

# --------------------------------------------------------------------------- #
# 1. Establish the canonical remote state. Never trust the local ref alone.
# --------------------------------------------------------------------------- #
echo ">> Fetching remote branch state..."
if ! git fetch --quiet "$REMOTE" "$BRANCH" 2>/dev/null; then
  echo "   ! could not fetch $REMOTE/$BRANCH -- working offline from local refs only"
fi
REMOTE_SHA="$(git ls-remote --heads "$REMOTE" "$BRANCH" 2>/dev/null | awk '{print $1}')"
if [ -z "$REMOTE_SHA" ]; then
  echo "   ! no remote branch found; aborting rather than guessing."
  exit 1
fi
echo "   remote tip: ${REMOTE_SHA:0:12}"

# --------------------------------------------------------------------------- #
# 2. Is there work that exists ONLY locally? If so, stop and show it.
# --------------------------------------------------------------------------- #
LOCAL_COMMITS="$(git log --oneline "$REMOTE_SHA"..HEAD 2>/dev/null | wc -l | tr -d ' ')"
DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"

# Files present on disk that the remote tip does NOT know about: these would be
# destroyed by a hard reset. (git status alone is not enough -- after a reset
# the index points at an older commit, so committed files show up as untracked.)
echo ">> Comparing the working tree against the remote tip..."
mapfile -t LOCAL_ONLY < <(
  python3 - "$REMOTE_SHA" <<'PY'
import os, subprocess, sys
sha = sys.argv[1]
r = subprocess.run(['git','ls-tree','-r','--name-only',sha],
                   capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(0)
remote = set(r.stdout.split())
ign = set()
for rec in subprocess.run(['git','status','--porcelain','--ignored','-z'],
                          capture_output=True).stdout.split(b'\0'):
    if rec[:2] == b'!!':
        ign.add(rec[3:].decode('utf-8','replace').rstrip('/'))
skip = {'.git','node_modules','__pycache__','.venv','.venv-ql','.pytest_cache',
        '.mypy_cache','.ruff_cache','dist','build','.next','.turbo','out',
        '.cache','.local','.arena'}
out = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in skip]
    for f in files:
        p = os.path.relpath(os.path.join(root, f), '.')
        if p not in remote and p not in ign:
            out.append(p)
print('\n'.join(sorted(out)))
PY
)

if [ "${#LOCAL_ONLY[@]}" -gt 0 ] && [ -n "${LOCAL_ONLY[0]}" ]; then
  hr
  echo "!! LOCAL-ONLY FILES PRESENT -- these are NOT in the remote tip."
  echo "!! A reset would delete them. They are listed below."
  hr
  printf '   %s\n' "${LOCAL_ONLY[@]}"
  hr
  echo "Nothing will be reset until these are committed, stashed, or moved."
  exit 2
fi

# Differs-from-remote check: any tracked file whose bytes differ from the tip.
mapfile -t DIFFERING < <(
  python3 - "$REMOTE_SHA" <<'PY'
import hashlib, os, subprocess, sys
sha = sys.argv[1]
r = subprocess.run(['git','ls-tree','-r',sha], capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(0)
for line in r.stdout.strip().split('\n'):
    meta, path = line.split('\t', 1)
    mode, typ, blob = meta.split()
    if typ != 'blob' or not os.path.isfile(path):
        continue
    got = subprocess.run(['git','hash-object','--path',path,path],
                         capture_output=True, text=True).stdout.strip()
    if got != blob:
        print(path)
PY
)

hr
echo "Local commits not on the remote : $LOCAL_COMMITS"
echo "Working-tree entries            : $DIRTY"
echo "Files differing from remote tip : ${#DIFFERING[@]}"
if [ "${#DIFFERING[@]}" -gt 0 ] && [ -n "${DIFFERING[0]}" ]; then
  printf '   %s\n' "${DIFFERING[@]}"
fi
hr

if [ "$LOCAL_COMMITS" != "0" ]; then
  echo "!! $LOCAL_COMMITS local commit(s) are not on the remote."
  echo "   They are safe where they are; push them before doing anything else."
  exit 2
fi

if [ "${#DIFFERING[@]}" -gt 0 ] && [ -n "${DIFFERING[0]}" ]; then
  echo "!! Working tree differs from the remote tip. Not resetting automatically."
  exit 2
fi

# --------------------------------------------------------------------------- #
# 3. Safe to restore the branch pointer. --mixed leaves the working tree alone,
#    and we have just proven the working tree already matches the remote tip.
# --------------------------------------------------------------------------- #
LOCAL_SHA="$(git rev-parse HEAD 2>/dev/null)"
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  echo ">> HEAD is behind the remote tip; moving the branch pointer (--mixed)."
  echo "   The working tree is untouched and was verified to already match."
  read -r -p "   Proceed? [y/N] " ans
  case "$ans" in
    [yY]*) git reset --mixed "$REMOTE_SHA" ;;
    *) echo "   Aborted at your request."; exit 0 ;;
  esac
fi

git config "branch.$BRANCH.remote" "$REMOTE"
git config "branch.$BRANCH.merge" "refs/heads/$BRANCH"
echo ">> HEAD now $(git rev-parse --short HEAD)"

# --------------------------------------------------------------------------- #
# 4. Python environment.
# --------------------------------------------------------------------------- #
if [ ! -x "$VENV/bin/python" ]; then
  echo ">> Rebuilding the Python venv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip setuptools wheel
  "$VENV/bin/pip" install -q -r backend/requirements.txt
  "$VENV/bin/pip" install -q -r frontend/requirements.txt
  # Pins that keep the two requirement sets installable together.
  "$VENV/bin/pip" install -q "pyarrow<17" "starlette<0.42"
else
  echo ">> Python venv already present."
fi
"$VENV/bin/pip" check || echo "   ! pip check reported conflicts"

# --------------------------------------------------------------------------- #
# 5. Frontend dependencies.
#
#    Order matters, and there are two traps here:
#
#      * `npm install` must run in frontend/web ONLY. Running it inside
#        frontend/circuit_composer/frontend installs a SECOND copy of React;
#        the bundle then fails at runtime with "invalid hook call"
#        (observed as: TypeError: Cannot read properties of null (reading
#        'useMemo') at Composer.tsx) instead of failing at build time.
#
#      * frontend/node_modules must be populated by scripts/link-shared.mjs,
#        which symlinks react / react-dom / @types / streamlit-component-lib
#        to the frontend/web copies so that the shared grid source resolves
#        exactly one React. Earlier revisions of this script skipped that step,
#        which left `npm run render:check` unable to resolve React at all.
# --------------------------------------------------------------------------- #
if [ ! -d frontend/web/node_modules ]; then
  echo ">> Installing frontend/web dependencies..."
  ( cd frontend/web && npm install --no-audit --no-fund )
else
  echo ">> frontend/web/node_modules already present."
fi

COMPOSER_NM="frontend/circuit_composer/frontend/node_modules"
if [ -d "$COMPOSER_NM/react" ]; then
  echo "!! $COMPOSER_NM/react exists -- this is a second copy of React."
  echo "   Removing it so render:check sees only one."
  rm -rf "$COMPOSER_NM"
fi

echo ">> Linking shared frontend dependencies (scripts/link-shared.mjs)..."
( cd frontend/web && node scripts/link-shared.mjs )

# --------------------------------------------------------------------------- #
# 6. Baseline checks.
# --------------------------------------------------------------------------- #
hr
echo ">> Done. Verify with:"
echo "   (cd backend && PYTHONPATH=. $VENV/bin/python -m pytest -q)"
echo "   $VENV/bin/python -m pytest frontend/tests -q"
echo "   (cd backend/scripts && $VENV/bin/python validate_lesson.py)"
echo "   node backend/scripts/check_lesson_math.mjs            # from repo root"
echo "   (cd frontend/web && npm run render:check)"
hr
