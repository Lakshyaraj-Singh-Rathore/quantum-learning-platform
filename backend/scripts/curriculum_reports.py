"""Generate the curriculum mapping and content-gap reports.

Run from the repository root:

    python3 backend/scripts/curriculum_reports.py

Both reports are derived from the registry in ``app/curriculum.py`` and from
the real lesson files in ``content/``. Nothing here authors content: the gap
report names what is missing so M4 can plan it, and deliberately does not
create it.

Outputs:
    docs/CURRICULUM_MAPPING.md      human-readable mapping report
    docs/CURRICULUM_MAPPING.json    same data, machine-readable
    docs/CONTENT_GAP_REPORT.md      coverage against the target curriculum
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.curriculum import (  # noqa: E402
    LEGACY_MAPPING_EVIDENCE,
    LEGACY_TAG_TO_TOPIC,
    LESSON_TOPIC_EVIDENCE,
    NAMESPACES,
    REVIEW_REQUIRED,
    SECTIONS,
    TOPICS,
    all_lesson_topics,
)

CONTENT_DIR = ROOT / "content"

#: The target curriculum from the roadmap, sectioned as in the master prompt.
#: Used only to report coverage; it does not create topics.
TARGET_CURRICULUM: dict[str, list[str]] = {
    "A Mathematical Foundations": [
        "Complex Numbers and Euler's Formula", "Linear Algebra", "Vectors and Matrices",
        "Eigenvalues and Eigenvectors", "Hermitian and Unitary Matrices", "Change of Basis",
        "Probability, Expectation and Variance", "Sampling Error and Confidence Intervals",
        "Introductory Group Theory",
    ],
    "B Core Quantum Theory": [
        "Quantum Postulates", "Measurement Theory and POVMs", "Pure and Mixed States",
        "Density Matrices", "Partial Trace and Reduced States", "Quantum Interference",
        "Relative and Global Phase", "Quantum Channels", "Entanglement Entropy and Monogamy",
        "No-Cloning and No-Deleting",
    ],
    "C Introduction to Quantum Computing": [
        "Quantum Mechanics", "Qubits", "Dirac Notation", "Tensor Products", "Inner Product",
        "Superposition", "Bell States", "Basic Quantum Gates",
        "Understanding Circuits and Finding Results", "Quantum Teleportation",
    ],
    "D Introduction to Qiskit": [
        "Quantum Composer", "Sampler", "Estimator", "Bloch Sphere", "Histograms",
        "Quantum Noise",
    ],
    "E Quantum Algorithms": [
        "Bernstein-Vazirani", "Deutsch-Jozsa", "Grover's Search", "Quantum Fourier Transform",
        "Quantum Phase Estimation", "Shor's Algorithm", "Simon's Algorithm", "Quantum Walks",
        "Amplitude Estimation", "HHL", "Quantum Key Distribution",
    ],
    "F Advanced Gates and Circuits": [
        "Toffoli and Multi-Controlled Gates", "Controlled Rotations", "U3, iSWAP and fSim",
        "Quantum Universality", "Circuit Identities and Simplification", "GHZ versus W States",
        "Transpilation", "Native Gates and Connectivity", "Routing and SWAP Insertion",
        "Resource Estimation",
    ],
    "G Variational and NISQ Algorithms": [
        "Parameterized Quantum Circuits", "Variational Quantum Eigensolver",
        "Ansatz Construction", "Classical Optimization Loops", "QAOA", "Approximation Ratios",
        "Parameter-Shift Rule", "Barren Plateaus", "Quantum Machine Learning",
        "Quantum Feature Maps and Kernels", "Dequantization Critiques",
    ],
    "H Error Correction and Fault Tolerance": [
        "Three-Qubit Bit-Flip Code", "Three-Qubit Phase-Flip Code", "Stabilizer Formalism",
        "Surface Codes", "Logical and Physical Qubits", "Threshold Theorem",
        "Error-Correction Overhead", "Fault Tolerance", "Zero-Noise Extrapolation",
        "Probabilistic Error Cancellation", "Readout Mitigation",
    ],
    "I Hardware and Ecosystem": [
        "Superconducting Qubits", "Trapped Ions", "Photonic Systems", "Neutral Atoms",
        "Spin-Based Qubits", "Calibrated Noise Models", "Connectivity Topologies",
        "NISQ Limitations", "BQP, P, NP and BPP", "Quantum Benchmarking",
        "Quantum Ecosystem: Qiskit, Cirq, PennyLane, CUDA-Q and Braket",
    ],
    "J Communication and Simulation": [
        "Superdense Coding", "Quantum Repeaters", "Quantum Internet", "Quantum Cryptography",
        "Post-Quantum Cryptography", "Quantum Simulation", "Trotterization",
        "Quantum Many-Body Systems",
    ],
}

#: Which registry topics address each target item. "partial" means existing
#: lessons touch it without covering the intended scope; None means absent.
COVERAGE: dict[str, tuple[str | None, str]] = {
    # B
    "Measurement Theory and POVMs": ("core.measurement_theory", "partial"),
    "Quantum Interference": ("core.quantum_interference", "partial"),
    "Quantum Channels": ("core.quantum_channels", "partial"),
    # C
    "Qubits": ("qc.qubits", "existing"),
    "Superposition": ("qc.superposition", "partial"),
    "Bell States": ("qc.bell_states", "existing"),
    "Basic Quantum Gates": ("qc.basic_gates", "existing"),
    "Understanding Circuits and Finding Results": (None, "missing"),
    "Quantum Mechanics": (None, "missing"),
    "Dirac Notation": (None, "missing"),
    "Tensor Products": (None, "missing"),
    "Inner Product": (None, "missing"),
    "Quantum Teleportation": (None, "missing"),
    # D
    "Sampler": ("qiskit.sampler", "partial"),
    "Quantum Noise": ("qiskit.quantum_noise", "existing"),
    "Quantum Composer": (None, "missing"),
    "Estimator": (None, "missing"),
    "Bloch Sphere": (None, "missing"),
    "Histograms": (None, "missing"),
    # E
    "Deutsch-Jozsa": ("algo.deutsch_jozsa", "existing"),
    "Grover's Search": ("algo.grover", "existing"),
    "Bernstein-Vazirani": (None, "missing"),
    "Quantum Fourier Transform": (None, "missing"),
    "Quantum Phase Estimation": (None, "missing"),
    "Shor's Algorithm": (None, "missing"),
    "Simon's Algorithm": (None, "missing"),
    "Quantum Walks": (None, "missing"),
    "Amplitude Estimation": (None, "missing"),
    "HHL": (None, "missing"),
    "Quantum Key Distribution": (None, "missing"),
    # F
    "Quantum Universality": ("adv.quantum_universality", "partial"),
    "Toffoli and Multi-Controlled Gates": (None, "missing"),
    "Controlled Rotations": (None, "missing"),
    "U3, iSWAP and fSim": (None, "missing"),
    "Circuit Identities and Simplification": (None, "missing"),
    "GHZ versus W States": (None, "missing"),
    "Transpilation": (None, "missing"),
    "Native Gates and Connectivity": (None, "missing"),
    "Routing and SWAP Insertion": (None, "missing"),
    "Resource Estimation": (None, "missing"),
    # G
    "Variational Quantum Eigensolver": ("nisq.vqe", "existing"),
    "QAOA": ("nisq.qaoa", "partial"),
    "Parameterized Quantum Circuits": ("nisq.parameterized_circuits", "partial"),
    "Ansatz Construction": (None, "missing"),
    "Classical Optimization Loops": (None, "missing"),
    "Approximation Ratios": (None, "missing"),
    "Parameter-Shift Rule": (None, "missing"),
    "Barren Plateaus": (None, "missing"),
    "Quantum Machine Learning": (None, "missing"),
    "Quantum Feature Maps and Kernels": (None, "missing"),
    "Dequantization Critiques": (None, "missing"),
}


def lesson_meta(slug: str) -> dict[str, Any]:
    path = CONTENT_DIR / f"{slug}.md"
    if not path.exists():
        return {"words": 0, "headings": [], "title": slug}
    text = path.read_text(encoding="utf-8")
    headings = [
        re.sub(r"^#+\s*", "", line).strip()
        for line in text.splitlines()
        if re.match(r"^#{1,3}\s", line)
    ]
    title = headings[0] if headings else slug
    return {
        "words": len(text.split()),
        "headings": headings[:8],
        "title": title,
        "sections": len([h for h in headings]),
    }


def build_mapping() -> list[dict[str, Any]]:
    topics_by_id = {str(t["id"]): t for t in TOPICS}
    rows: list[dict[str, Any]] = []
    for slug, topic_id, confidence, is_primary in all_lesson_topics():
        topic = topics_by_id[topic_id]
        key = f"{slug}::{topic_id}"
        meta = lesson_meta(slug)
        rows.append({
            "lesson_slug": slug,
            "lesson_title": meta["title"],
            "lesson_words": meta["words"],
            "topic_id": topic_id,
            "topic_title": str(topic["title"]),
            "section": NAMESPACES[str(topic["namespace"])][2],
            "relationship": "primary" if is_primary else "secondary",
            "confidence": confidence,
            "evidence": LESSON_TOPIC_EVIDENCE.get(key, ""),
            "basis": "content-derived" if LESSON_TOPIC_EVIDENCE.get(key) else "MISSING",
            "inferred": False,
            "needs_review": False,
        })
    rows.sort(key=lambda r: (r["lesson_slug"], 0 if r["relationship"] == "primary" else 1))
    return rows


def write_mapping_md(rows: list[dict[str, Any]], out: Path) -> None:
    counts = Counter(r["confidence"] for r in rows)
    lines = [
        "# Curriculum Mapping Report",
        "",
        "Generated by `backend/scripts/curriculum_reports.py` from the registry in",
        "`backend/app/curriculum.py` and the real lesson files in `content/`.",
        "Regenerate rather than editing by hand.",
        "",
        f"- Lesson-to-topic mappings: **{len(rows)}**",
        f"- High confidence: **{counts.get('high', 0)}**",
        f"- Medium confidence: **{counts.get('medium', 0)}**",
        f"- Low confidence: **{counts.get('low', 0)}**",
        f"- Primary relationships: **{sum(1 for r in rows if r['relationship'] == 'primary')}**",
        f"- Secondary relationships: **{sum(1 for r in rows if r['relationship'] == 'secondary')}**",
        "",
        "## Confidence definitions",
        "",
        "- **high** — the lesson's actual content directly and unambiguously",
        "  corresponds to the topic.",
        "- **medium** — content strongly corresponds but the lesson spans several",
        "  concepts, or the curriculum boundary is somewhat ambiguous.",
        "- **low** — primarily inferred from indirect evidence, filenames, broad",
        "  assessment tags, or current structure. Low-confidence mappings never",
        "  grant mastery and never gate prerequisites.",
        "",
        "Only **high** confidence may carry legacy mastery onto a topic",
        "(`MASTERY_MAPPABLE_CONFIDENCE`).",
        "",
        "## Mappings",
        "",
    ]

    by_lesson: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_lesson[row["lesson_slug"]].append(row)

    for slug in sorted(by_lesson):
        entries = by_lesson[slug]
        lines.append(f"### `{slug}` — {entries[0]['lesson_title']}")
        lines.append("")
        lines.append(f"*{entries[0]['lesson_words']} words*")
        lines.append("")
        lines.append("| Topic | Relationship | Confidence | Basis |")
        lines.append("|---|---|---|---|")
        for e in entries:
            lines.append(
                f"| `{e['topic_id']}` | {e['relationship']} | **{e['confidence']}** | "
                f"{e['basis']} |"
            )
        lines.append("")
        for e in entries:
            lines.append(f"- **`{e['topic_id']}`** — {e['evidence']}")
        lines.append("")

    lines += [
        "## Legacy assessment tag mapping",
        "",
        "Mastery rows are written from authored quiz and challenge tags, not from",
        "lesson prose. Each mapping below is backed by the assessment named in the",
        "evidence column.",
        "",
        "| Legacy tag | Topic | Evidence |",
        "|---|---|---|",
    ]
    for tag, topic in sorted(LEGACY_TAG_TO_TOPIC.items()):
        lines.append(f"| `{tag}` | `{topic}` | {LEGACY_MAPPING_EVIDENCE.get(tag, '')} |")
    lines.append("")

    lines += [
        "## Flagged for review",
        "",
        "These mappings rest on indirect evidence. They remain active but must not",
        "be treated as verified, and must not silently become authoritative.",
        "",
    ]
    for key, note in REVIEW_REQUIRED.items():
        lines.append(f"- **{key}** — {note}")
    lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")


def write_gap_report(out: Path) -> None:
    existing: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    by_section: dict[str, dict[str, list[str]]] = defaultdict(
        lambda: {"existing": [], "partial": [], "missing": []}
    )

    for section, items in TARGET_CURRICULUM.items():
        for item in items:
            topic_id, status = COVERAGE.get(item, (None, "missing"))
            label = f"{item}" + (f" (`{topic_id}`)" if topic_id else "")
            by_section[section][status].append(label)
            {"existing": existing, "partial": partial, "missing": missing}[status].append(item)

    total = len(existing) + len(partial) + len(missing)
    lines = [
        "# Curriculum Content Gap Report",
        "",
        "Generated by `backend/scripts/curriculum_reports.py`.",
        "",
        "This report **names what is missing**. It does not create it. Authoring is",
        "M4 and is deliberately kept out of the restructuring work so that content",
        "creation never blocks the structural change.",
        "",
        f"- Existing coverage: **{len(existing)}**",
        f"- Partial coverage: **{len(partial)}**",
        f"- Missing: **{len(missing)}**",
        f"- Target items: **{total}**",
        "",
        "Definitions:",
        "",
        "- **existing** — a registry topic has real lessons covering the intent.",
        "- **partial** — lessons touch the topic but do not cover the intended scope.",
        "- **missing** — no learning material corresponds to it.",
        "",
        "## By section",
        "",
    ]

    for section in TARGET_CURRICULUM:
        buckets = by_section[section]
        lines.append(f"### {section}")
        lines.append("")
        for status in ("existing", "partial", "missing"):
            items = buckets[status]
            if not items:
                continue
            lines.append(f"**{status.capitalize()} ({len(items)})**")
            lines.append("")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    lines += [
        "## M4 authoring priority",
        "",
        "Dependency-aware order, as specified in the roadmap:",
        "",
        "1. **Mathematical foundations** — complex numbers, linear algebra,",
        "   probability. Highest leverage: nearly every later topic assumes them.",
        "2. **Core quantum theory** — density matrices, POVMs, channels, phase.",
        "3. **QFT and phase estimation** — prerequisites for Shor.",
        "4. **Bernstein-Vazirani** — before Deutsch-Jozsa where pedagogically useful.",
        "5. **Noise and mitigation** — zero-noise extrapolation, readout mitigation.",
        "6. **Variational algorithms** — ansatz construction, parameter shift.",
        "7. **Error correction** — stabilizers, surface codes, threshold.",
        "8. **Hardware, communication and simulation**.",
        "",
        "## Not started",
        "",
        "No new lesson content was authored by this report.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = build_mapping()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)

    (docs / "CURRICULUM_MAPPING.json").write_text(
        json.dumps(
            {
                "generated_by": "backend/scripts/curriculum_reports.py",
                "mappings": rows,
                "legacy_tag_mapping": [
                    {"tag": t, "topic": tp, "evidence": LEGACY_MAPPING_EVIDENCE.get(t, "")}
                    for t, tp in sorted(LEGACY_TAG_TO_TOPIC.items())
                ],
                "review_required": REVIEW_REQUIRED,
                "sections": {str(s["slug"]): s["title"] for s in SECTIONS},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_mapping_md(rows, docs / "CURRICULUM_MAPPING.md")
    write_gap_report(docs / "CONTENT_GAP_REPORT.md")
    print(
        f"wrote {len(rows)} mappings and the gap report to {docs}"
    )


if __name__ == "__main__":
    main()
