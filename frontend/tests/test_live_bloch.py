"""The live Bloch component: packaging, and agreement with the Python maths.

``quantum.ts`` is a second implementation of physics ``lib/playground.py``
already gets right. That duplication is deliberate -- it buys continuous
interaction that a Streamlit rerun per drag cannot -- but it must not be
allowed to drift. The parity test below compares the two numerically.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PKG = ROOT / "live_bloch"
SRC = PKG / "frontend" / "src"
BUILD = PKG / "frontend" / "build"

from lib import playground as pg, viz  # noqa: E402


# ------------------------------------------------------------------ packaging
def test_component_package_exists():
    assert (PKG / "__init__.py").is_file()
    for name in ("quantum.ts", "Sphere.tsx", "LiveBloch.tsx", "index.tsx", "styles.css"):
        assert (SRC / name).is_file(), name


def test_component_pins_js_mime_type():
    """Slim base images have no /etc/mime.types; .js then fails to execute."""
    src = (PKG / "__init__.py").read_text()
    assert 'mimetypes.add_type("text/javascript", ".js")' in src


def test_component_is_not_wrapped_in_strict_mode():
    """StrictMode double-mounts and the RENDER listener can be lost."""
    assert "<React.StrictMode>" not in (SRC / "index.tsx").read_text()


def test_frame_height_is_clamped():
    """A reported height of 0 collapses the iframe into a blank white box."""
    src = (SRC / "index.tsx").read_text()
    assert "MIN_FRAME_HEIGHT" in src
    assert "Math.max" in src


def test_component_self_heals_when_blank():
    src = (SRC / "index.tsx").read_text()
    assert "childElementCount" in src
    assert "setComponentReady" in src


def test_commit_to_streamlit_is_debounced():
    """Committing per pointer move would rerun the page mid-gesture."""
    src = (SRC / "LiveBloch.tsx").read_text()
    assert "COMMIT_DELAY_MS" in src
    assert "setTimeout" in src


def test_dockerfile_builds_and_ships_the_bundle():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "AS bloch" in dockerfile
    assert "COPY --from=bloch /bloch/build ./live_bloch/frontend/build" in dockerfile


def test_build_output_is_gitignored():
    assert "build/" in (PKG / "frontend" / ".gitignore").read_text()


@pytest.mark.skipif(not BUILD.exists(), reason="bundle not built")
def test_bundle_is_self_consistent():
    from live_bloch import build_is_consistent

    ok, problem = build_is_consistent()
    assert ok, problem


# --------------------------------------------------- python <-> typescript
NODE = shutil.which("node")

_PARITY_SCRIPT = r"""
const fs = require('fs');
let src = fs.readFileSync(process.argv[2], 'utf8');
src = src
  .replace(/export (const|function|type)/g, '$1')
  .replace(/^export .*$/gm, '')
  .replace(/: *Record<[^>]+>/g, '')
  .replace(/: *\[Complex, *Complex, *Complex, *Complex\]/g, '')
  .replace(/: *Complex\b/g, '')
  .replace(/: *State\b/g, '')
  .replace(/: *number\b/g, '')
  .replace(/: *string\[\]/g, '')
  .replace(/: *string\b/g, '')
  .replace(/: *\[number, *number, *number\]/g, '')
  .replace(/: *\[number, *number\]/g, '')
  .replace(/type .*?=.*?\n/g, '')
  .replace(/ as \w+/g, '');
const m = new Function(
  src + ';return {stateFromAngles,applyGates,probabilities,blochVector,blochAngles};'
)();
const out = [];
for (const th of [0, 17, 30, 90, 143, 180])
  for (const ph of [0, 45, 90, 180, 270, 333]) {
    const s = m.stateFromAngles(th, ph);
    out.push({th, ph, gates: [], v: m.blochVector(s), p: m.probabilities(s)});
  }
for (const g of [['H'], ['X'], ['Y'], ['Z'], ['S'], ['T'], ['H','T'], ['H','Z','H'], ['T','T','S']]) {
  const s = m.applyGates(m.stateFromAngles(90, 0), g);
  out.push({th: 90, ph: 0, gates: g, v: m.blochVector(s), p: m.probabilities(s)});
}
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node is not available")
def test_typescript_matches_the_verified_python():
    """The two implementations must agree to floating-point noise."""
    script = Path("/tmp/_parity.cjs")
    script.write_text(_PARITY_SCRIPT)
    result = subprocess.run(
        [NODE, str(script), str(SRC / "quantum.ts")],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr[-500:]
    cases = json.loads(result.stdout)
    assert len(cases) >= 40

    worst = 0.0
    for case in cases:
        state = pg.state_from_angles(case["th"], case["ph"])
        if case["gates"]:
            state = pg.apply_gates(state, case["gates"])
        rho = np.outer(state, state.conj())
        worst = max(
            worst,
            float(np.abs(np.array(viz.bloch_vector(rho)) - np.array(case["v"])).max()),
            float(np.abs(np.array(pg.probabilities(state)) - np.array(case["p"])).max()),
        )
    assert worst < 1e-9, f"TypeScript and Python diverged by {worst:.2e}"


def test_typescript_gate_set_matches_python():
    """A gate added on one side only would silently teach different physics."""
    ts = (SRC / "quantum.ts").read_text()
    ts_gates = set()
    block = ts[ts.index("export const GATES"):ts.index("export const GATE_HELP")]
    for name in pg.GATES:
        if f"{name}:" in block:
            ts_gates.add(name)
    assert ts_gates == set(pg.GATES)


def test_typescript_landmarks_match_python():
    ts = (SRC / "quantum.ts").read_text()
    block = ts[ts.index("export const LANDMARKS"):ts.index("export function stateFromAngles")]
    for name, (theta, phi) in pg.LANDMARKS.items():
        assert name in block, name
        assert f"[{theta:.0f}, {phi:.0f}]" in block, f"{name} angles differ"


def test_python_fallback_still_exists():
    """If the bundle is missing, lessons must still show a Bloch sphere."""
    from lib import lesson_demos

    src = (ROOT / "lib" / "lesson_demos.py").read_text()
    assert "_bloch_available()" in src
    assert "viz.bloch_sphere" in src
    assert callable(lesson_demos.bloch_explorer)
