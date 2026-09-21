"""The timeline is a default-on feature and must not disturb the composer.

Reported symptom: pressing "Build / refresh timeline" turned the drag-and-drop
composer into a blank white box, and the only way back was to change the qubit
count (which forced the component to remount).

Cause: Streamlit addresses a custom component by its position in the element
tree. Building the timeline added four transport buttons and a results table
ABOVE the composer, so Streamlit tore the iframe down and recreated it -- and a
recreated component can miss Streamlit's one-shot RENDER event and paint null.

Two defences, both locked down here:
  1. The composer is written into a container allocated before the timeline, so
     its path no longer depends on how big the timeline is.
  2. The timeline builds automatically instead of behind a button, so the
     element count above the composer does not change mid-session.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "2_Composer.py"
STRIP = ROOT / "lib" / "timeline_strip.py"


def test_timeline_has_no_build_button():
    """The button press was what tore the component down."""
    src = STRIP.read_text()
    # Ignore prose: only executable lines matter.
    code = "\n".join(
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    )
    code = code.split('"""')[0] + '"""'.join(code.split('"""')[2::2])
    assert "st.button(" not in code
    assert 'key="build_timeline"' not in code


def test_timeline_builds_automatically():
    src = STRIP.read_text()
    assert "circuit_timeline" in src
    # It must self-populate rather than waiting for an interaction.
    assert "timeline_signature" in src


def test_timeline_refreshes_when_the_circuit_changes():
    """A cached timeline from a different circuit must not be shown."""
    from lib import timeline_strip

    a = {"n_qubits": 2, "n_clbits": 2, "ops": []}
    b = {"n_qubits": 5, "n_clbits": 5, "ops": []}
    assert timeline_strip._signature(a) != timeline_strip._signature(b)


def test_signature_is_key_order_independent():
    from lib import timeline_strip

    a = {"n_qubits": 2, "ops": [], "n_clbits": 2}
    b = {"ops": [], "n_clbits": 2, "n_qubits": 2}
    assert timeline_strip._signature(a) == timeline_strip._signature(b)


def test_composer_container_is_allocated_before_the_timeline():
    """Element path stability: the slot must exist before the timeline fills."""
    src = PAGE.read_text()
    composer_slot = src.index("composer_slot = st.container()")
    timeline_render = src.index("timeline_strip.render(")
    assert composer_slot < timeline_render, (
        "the composer's container must be created before the timeline renders, "
        "otherwise the timeline's widgets shift the component's position"
    )


def test_component_is_rendered_into_the_reserved_slot():
    src = PAGE.read_text()
    assert "with composer_slot:" in src
    assert "circuit_composer(" in src


def test_component_self_heals_when_blank():
    """A torn-down component must re-announce readiness, not stay white."""
    index_tsx = ROOT / "circuit_composer" / "frontend" / "src" / "index.tsx"
    src = index_tsx.read_text()
    assert "childElementCount" in src
    assert "setComponentReady" in src
    # The watchdog must not give up after a fixed number of attempts, because
    # a teardown can happen at any point in a long session.
    assert "attempts >= 5" not in src
