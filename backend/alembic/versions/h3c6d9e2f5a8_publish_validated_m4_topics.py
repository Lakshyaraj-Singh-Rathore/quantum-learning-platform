"""Publish the M4 topics whose lessons are authored and validated.

M4 registered 54 topics as ``draft`` so the curriculum would have a stable
identity to author against before any content existed. The reader only ever
shows ``published`` topics (see ``build_curriculum``), on the grounds that a
draft topic has no content and an unopenable entry is bad navigation.

The counterpart to that rule was always that a draft is published once its
lesson is authored and validated. Every one of the 54 has now reached that
point: each has at least one lesson, and every lesson it declares is marked
``verified`` in the rewrite tracker. Leaving them drafts is what makes the
curriculum read as empty.

The list is EXPLICIT rather than derived from the tracker or the registry at
run time, for two reasons: the api container mounts only ./backend, ./content
and ./samples, so docs/ is not readable from inside a migration; and an
explicit list keeps the downgrade exact, since it never has to guess which
rows it changed.

Revision ID: h3c6d9e2f5a8
Revises: g2a5b8c1d4e7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h3c6d9e2f5a8"
down_revision: Union[str, None] = "g2a5b8c1d4e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: Drafts whose every declared lesson is verified, and so are safe to show.
PUBLISHED_TOPIC_IDS = frozenset(
    {
        "adv.circuit_identities",
        "adv.compilation",
        "adv.multi_controlled_gates",
        "adv.multipartite_entanglement",
        "adv.parameterized_two_qubit",
        "adv.resource_estimation",
        "algo.amplitude_estimation",
        "algo.bernstein_vazirani",
        "algo.hhl",
        "algo.phase_estimation",
        "algo.qft",
        "algo.quantum_walks",
        "algo.shors",
        "algo.simon",
        "comm.cryptography",
        "comm.quantum_networks",
        "comm.quantum_simulation",
        "comm.superdense_coding",
        "comm.trotterization",
        "core.density_matrices",
        "core.entanglement_measures",
        "core.no_cloning",
        "core.quantum_postulates",
        "hw.benchmarking",
        "hw.complexity_classes",
        "hw.ecosystem",
        "hw.neutral_atoms",
        "hw.nisq_limitations",
        "hw.photonic_systems",
        "hw.platform_comparison",
        "hw.spin_qubits",
        "hw.superconducting_qubits",
        "hw.trapped_ions",
        "math.complex_numbers",
        "math.eigen_and_operators",
        "math.group_theory",
        "math.linear_algebra",
        "math.probability_and_statistics",
        "nisq.approximation_ratios",
        "nisq.optimization",
        "nisq.qml",
        "qc.dirac_notation",
        "qc.reading_results",
        "qc.teleportation",
        "qc.tensor_products",
        "qec.bit_flip_code",
        "qec.error_mitigation",
        "qec.logical_physical",
        "qec.phase_flip_code",
        "qec.stabilizer_formalism",
        "qec.surface_codes",
        "qec.threshold_theorem",
        "qiskit.composer",
        "qiskit.estimator",
    }
)


def upgrade() -> None:
    bind = op.get_bind()
    for topic_id in sorted(PUBLISHED_TOPIC_IDS):
        bind.execute(
            sa.text(
                "UPDATE curriculum_topics SET status = 'published' "
                "WHERE id = :id AND status = 'draft'"
            ),
            {"id": topic_id},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for topic_id in sorted(PUBLISHED_TOPIC_IDS):
        bind.execute(
            sa.text(
                "UPDATE curriculum_topics SET status = 'draft' "
                "WHERE id = :id AND status = 'published'"
            ),
            {"id": topic_id},
        )
