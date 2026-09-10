"""Result visualizations: histogram, probability table, phase disk, Bloch, circuit."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

MAX_HISTOGRAM_BARS = 32


# --------------------------------------------------------------------------- #
# Counts
# --------------------------------------------------------------------------- #
def histogram(
    result: dict[str, Any],
    color_by_phase: bool = False,
    as_probability: bool = False,
) -> None:
    """Counts histogram, optionally tinted by each outcome's relative phase.

    Phase colouring is the only way to see a Z/S/T/RZ gate on a histogram:
    those gates change the phase without moving a single count, so the bars
    are identical and only the colour differs.
    """
    counts: dict[str, int] = result.get("counts") or {}
    if not counts:
        st.info("No counts to display - the circuit has no measurements.")
        return

    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    truncated = len(items) > MAX_HISTOGRAM_BARS
    if truncated:
        items = items[:MAX_HISTOGRAM_BARS]
    items.sort(key=lambda kv: kv[0])

    total = sum(counts.values()) or 1
    labels = [k for k, _ in items]
    raw_values = [v for _, v in items]
    values = [v / total for v in raw_values] if as_probability else raw_values

    phase_lookup: dict[str, float] = {}
    amplitudes = _amplitudes(result)
    if color_by_phase and amplitudes is not None:
        n_bits = int(math.log2(len(amplitudes)))
        relative = _relative_phases(amplitudes)
        for index in range(len(amplitudes)):
            if abs(amplitudes[index]) ** 2 > 1e-12:
                phase_lookup[format(index, f"0{n_bits}b")] = float(
                    np.degrees(relative[index])
                )

    use_phase = color_by_phase and bool(phase_lookup)
    if use_phase:
        marker = dict(
            color=[phase_lookup.get(k, 0.0) for k in labels],
            colorscale=PHASE_CSCALE,
            cmin=-180,
            cmax=180,
            showscale=True,
            colorbar=dict(
                title=dict(text="rel. phase", side="right"),
                tickvals=[-180, -90, 0, 90, 180],
                ticktext=["-180", "-90", "0", "+90", "+180"],
                len=0.75,
            ),
        )
        hover = [
            f"<b>|{k}></b><br>count {v} ({v / total:.2%})<br>rel. phase "
            + (f"{phase_lookup[k]:+.1f} deg" if k in phase_lookup else "n/a")
            for k, v in items
        ]
    else:
        marker = dict(color="#6C5CE7")
        hover = [f"<b>|{k}></b><br>count {v} ({v / total:.2%})" for k, v in items]

    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            text=[
                f"{v / total:.3f}" if as_probability else f"{v}<br>{v / total:.1%}"
                for v in raw_values
            ],
            textposition="outside",
            marker=marker,
            hovertext=hover,
            hoverinfo="text",
        )
    )
    figure.update_layout(
        xaxis_title="Bitstring (qubit 0 = rightmost)",
        yaxis_title="Probability" if as_probability else "Counts",
        margin=dict(l=10, r=10, t=30, b=10),
        height=360,
        showlegend=False,
    )
    # Bitstrings like "00", "01", "10" are numeric-looking, so Plotly infers a
    # LINEAR axis and places them at 0, 1, 10, 11 -- which rendered as ticks
    # 0,2,4,6,8,10 with bars in the wrong places and labels that looked like
    # plain numbers. Forcing a categorical axis keeps one slot per bitstring.
    figure.update_xaxes(type="category")
    st.plotly_chart(figure, use_container_width=True)
    if use_phase:
        st.caption(
            "Bar colour is the **relative phase** of that basis state. Z / S / T / RZ "
            "change the colour without changing any bar height."
        )
    elif color_by_phase:
        st.caption("Phase colouring needs a statevector; this run does not have one.")
    if truncated:
        st.caption(f"Showing the {MAX_HISTOGRAM_BARS} most frequent of {len(counts)} outcomes.")


def probability_table(result: dict[str, Any]) -> None:
    counts: dict[str, int] = result.get("counts") or {}
    if not counts:
        return
    total = sum(counts.values()) or 1
    frame = pd.DataFrame(
        [
            {
                "Bitstring": key,
                "Counts": value,
                "Probability": value / total,
                "Percent": f"{value / total:.2%}",
            }
            for key, value in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        ]
    )
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Probability": st.column_config.ProgressColumn(
                "Probability", min_value=0.0, max_value=1.0, format="%.4f"
            )
        },
    )


# --------------------------------------------------------------------------- #
# Statevector views
# --------------------------------------------------------------------------- #
def _amplitudes(result: dict[str, Any]) -> np.ndarray | None:
    raw = result.get("statevector")
    if not raw:
        return None
    return np.array([complex(re, im) for re, im in raw])


PHASE_CSCALE = [
    [0.00, "rgb(61,214,198)"],
    [0.25, "rgb(91,157,255)"],
    [0.50, "rgb(225,124,255)"],
    [0.75, "rgb(255,93,93)"],
    [1.00, "rgb(61,214,198)"],
]


def _relative_phases(amplitudes: np.ndarray) -> np.ndarray:
    """Phases with the global phase removed.

    A statevector is only defined up to an overall phase, so the raw
    ``np.angle`` of each amplitude is not physically meaningful on its own --
    only differences are. We divide out the phase of the first significant
    amplitude so the reference state sits at 0 degrees and every other angle
    is a genuine *relative* phase.
    """
    probabilities = np.abs(amplitudes) ** 2
    significant = np.flatnonzero(probabilities > 1e-12)
    if significant.size == 0:
        return np.angle(amplitudes)
    reference = np.angle(amplitudes[significant[0]])
    return np.angle(amplitudes * np.exp(-1j * reference))


def phase_disk(result: dict[str, Any]) -> None:
    """Phase disk: magnitude as radius, relative phase as angle, per basis state.

    Every basis state gets its own ring (radius band). Previously all states
    shared one radial scale, so in any equal-superposition -- H|0>, a Bell
    pair, GHZ -- the markers had identical magnitude *and* identical phase and
    landed on the exact same point, hiding every state but one. The complaint
    that the disk "shows the phase of only one state" was exactly this.
    """
    amplitudes = _amplitudes(result)
    if amplitudes is None:
        st.info(
            "Phase disk unavailable: this run has no statevector "
            "(mid-circuit measurement, reset or remote execution)."
        )
        return

    n_qubits = int(math.log2(len(amplitudes)))
    probabilities = np.abs(amplitudes) ** 2
    keep = probabilities > 1e-10
    if not keep.any():
        st.info("Statevector is empty.")
        return

    indices = np.flatnonzero(keep)
    if len(indices) > 32:
        indices = np.sort(indices[np.argsort(probabilities[indices])[::-1][:32]])

    relative = _relative_phases(amplitudes)
    angles = np.degrees(relative[indices])
    magnitudes = np.abs(amplitudes[indices])
    labels = [format(int(i), f"0{n_qubits}b") for i in indices]

    n_states = len(indices)
    figure = go.Figure()

    # One concentric ring per basis state keeps overlapping states distinct.
    for slot, (index, label) in enumerate(zip(indices, labels)):
        ring = (slot + 1) / n_states
        magnitude = float(magnitudes[slot])
        angle = float(angles[slot])
        probability = float(probabilities[index])

        figure.add_trace(
            go.Scatterpolar(
                r=[ring] * 73,
                theta=list(range(0, 361, 5)),
                mode="lines",
                line=dict(color="rgba(255,255,255,0.10)", width=1),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        # Radial spoke: length within the ring encodes |amplitude|.
        figure.add_trace(
            go.Scatterpolar(
                r=[ring - 1.0 / n_states * 0.92 * (1 - magnitude), ring],
                theta=[angle, angle],
                mode="lines",
                line=dict(color="rgba(255,255,255,0.35)", width=2),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatterpolar(
                r=[ring],
                theta=[angle],
                mode="markers+text",
                text=[f"|{label}>"],
                textposition="middle right",
                textfont=dict(size=11),
                marker=dict(
                    size=10 + 26 * math.sqrt(probability),
                    color=[angle],
                    colorscale=PHASE_CSCALE,
                    cmin=-180,
                    cmax=180,
                    showscale=slot == 0,
                    colorbar=dict(
                        title=dict(text="rel. phase", side="right"),
                        tickvals=[-180, -90, 0, 90, 180],
                        ticktext=["-180", "-90", "0", "+90", "+180"],
                        len=0.75,
                    )
                    if slot == 0
                    else None,
                    line=dict(width=1, color="rgba(255,255,255,0.45)"),
                ),
                hovertemplate=(
                    f"<b>|{label}></b><br>|amp| {magnitude:.4f}"
                    f"<br>probability {probability:.4f}"
                    f"<br>rel. phase {angle:+.1f} deg<extra></extra>"
                ),
                showlegend=False,
            )
        )

    figure.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 1.08], showticklabels=False, showgrid=False),
            angularaxis=dict(
                direction="counterclockwise",
                tickmode="array",
                tickvals=[0, 45, 90, 135, 180, 225, 270, 315],
                ticktext=["0", "45", "90", "135", "180", "-135", "-90", "-45"],
            ),
        ),
        margin=dict(l=30, r=30, t=30, b=30),
        height=460,
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Each basis state sits on its **own ring**, so states that share a phase no "
        "longer overlap. The angle is the phase **relative** to the first populated "
        "state (global phase is unobservable); marker size grows with probability."
    )


def qsphere(result: dict[str, Any]) -> None:
    """IBM-style Q-sphere: latitude = Hamming weight, colour = relative phase."""
    amplitudes = _amplitudes(result)
    if amplitudes is None:
        st.info("Q-sphere unavailable: this run has no statevector.")
        return

    n_qubits = int(math.log2(len(amplitudes)))
    probabilities = np.abs(amplitudes) ** 2
    relative = _relative_phases(amplitudes)

    by_weight: dict[int, list[int]] = {}
    for index in range(len(amplitudes)):
        if probabilities[index] > 1e-10:
            by_weight.setdefault(bin(index).count("1"), []).append(index)

    if not by_weight:
        st.info("Statevector is empty.")
        return

    figure = go.Figure()
    u = np.linspace(0, 2 * np.pi, 40)
    v = np.linspace(0, np.pi, 20)
    figure.add_surface(
        x=np.outer(np.cos(u), np.sin(v)),
        y=np.outer(np.sin(u), np.sin(v)),
        z=np.outer(np.ones_like(u), np.cos(v)),
        opacity=0.10,
        colorscale=[[0, "#8b95a5"], [1, "#8b95a5"]],
        showscale=False,
        hoverinfo="skip",
    )

    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    spoke_x: list[float | None] = []
    spoke_y: list[float | None] = []
    spoke_z: list[float | None] = []
    sizes: list[float] = []
    colors: list[float] = []
    hovers: list[str] = []
    texts: list[str] = []

    for weight, members in sorted(by_weight.items()):
        theta = np.pi * weight / max(n_qubits, 1)
        for slot, index in enumerate(sorted(members)):
            phi = 0.0 if len(members) <= 1 else 2 * np.pi * slot / len(members)
            x = float(np.sin(theta) * np.cos(phi))
            y = float(np.sin(theta) * np.sin(phi))
            z = float(np.cos(theta))
            probability = float(probabilities[index])
            degrees = float(np.degrees(relative[index]))
            label = format(index, f"0{n_qubits}b")
            xs.append(x)
            ys.append(y)
            zs.append(z)
            spoke_x += [0.0, x, None]
            spoke_y += [0.0, y, None]
            spoke_z += [0.0, z, None]
            sizes.append(8 + 26 * math.sqrt(probability))
            colors.append(degrees)
            texts.append(f"|{label}>")
            hovers.append(
                f"<b>|{label}></b><br>probability {probability:.4f}"
                f"<br>Hamming weight {weight}<br>rel. phase {degrees:+.1f} deg"
            )

    figure.add_trace(
        go.Scatter3d(
            x=spoke_x,
            y=spoke_y,
            z=spoke_z,
            mode="lines",
            line=dict(color="rgba(255,255,255,0.30)", width=3),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=xs,
            y=ys,
            z=zs,
            mode="markers+text",
            text=texts,
            textposition="top center",
            textfont=dict(size=10),
            marker=dict(
                size=sizes,
                color=colors,
                colorscale=PHASE_CSCALE,
                cmin=-180,
                cmax=180,
                showscale=True,
                colorbar=dict(title=dict(text="rel. phase", side="right"), len=0.75),
                line=dict(width=1, color="rgba(255,255,255,0.40)"),
            ),
            hovertext=hovers,
            hoverinfo="text",
            showlegend=False,
        )
    )
    figure.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=520,
        scene=dict(
            xaxis=dict(visible=False, range=[-1.4, 1.4]),
            yaxis=dict(visible=False, range=[-1.4, 1.4]),
            zaxis=dict(visible=False, range=[-1.4, 1.4]),
            aspectmode="cube",
        ),
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Latitude is Hamming weight: north pole is all-zeros, south pole is all-ones. "
        "Blob size is probability, colour is relative phase. This shows the **ideal "
        "statevector** -- it is not a Bloch sphere and cannot show a mixed state."
    )


def amplitude_table(result: dict[str, Any]) -> None:
    amplitudes = _amplitudes(result)
    if amplitudes is None:
        return
    n_qubits = int(math.log2(len(amplitudes)))
    rows = []
    for index, amplitude in enumerate(amplitudes):
        probability = float(abs(amplitude) ** 2)
        if probability <= 1e-10:
            continue
        rows.append(
            {
                "State": f"|{format(index, f'0{n_qubits}b')}>",
                "Amplitude": f"{amplitude.real:+.4f} {amplitude.imag:+.4f}i",
                "Probability": probability,
                "Phase (deg)": round(math.degrees(np.angle(amplitude)), 2),
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def bloch_sphere(result: dict[str, Any], summary: dict[str, Any] | None = None) -> None:
    """Bloch vectors per qubit - only meaningful for unitary circuits."""
    amplitudes = _amplitudes(result)
    if amplitudes is None:
        st.info(
            "Bloch sphere disabled: no statevector is available for this run "
            "(mid-circuit measurement, reset, or a remote backend)."
        )
        return
    if summary and summary.get("has_mid_circuit_measurement"):
        st.warning(
            "Bloch sphere disabled: the circuit contains a mid-circuit measurement, "
            "so the state is not a single pure state across shots."
        )
        return

    n_qubits = int(math.log2(len(amplitudes)))
    if n_qubits > 5:
        st.info("Bloch view is limited to 5 qubits.")
        return

    tensor = amplitudes.reshape([2] * n_qubits)

    # Entanglement report first: for a maximally entangled register every Bloch
    # vector is the zero vector, which looks like a broken plot unless we say
    # why. The length of a Bloch vector IS the single-qubit purity, so a short
    # arrow is physics, not a bug.
    entropies: list[float] = []
    purities: list[float] = []
    for qubit in range(n_qubits):
        axis = n_qubits - 1 - qubit
        moved = np.moveaxis(tensor, axis, 0).reshape(2, -1)
        rho = moved @ moved.conj().T
        purities.append(float(np.real(np.trace(rho @ rho))))
        eigenvalues = np.linalg.eigvalsh(rho)
        eigenvalues = np.clip(np.real(eigenvalues), 0.0, 1.0)
        nonzero = eigenvalues[eigenvalues > 1e-12]
        entropies.append(float(-np.sum(nonzero * np.log2(nonzero))) if nonzero.size else 0.0)

    max_entropy = max(entropies) if entropies else 0.0
    if n_qubits >= 2:
        if max_entropy > 0.99:
            st.warning(
                f"**Maximally entangled** (max single-qubit entropy "
                f"{max_entropy:.3f} bits). Every arrow below collapses to the "
                "centre. That is correct: an entangled qubit has **no** state of "
                "its own, so no Bloch arrow can describe it. Use the Q-sphere tab "
                "to see the state of the whole register."
            )
        elif max_entropy > 0.01:
            st.info(
                f"**Partially entangled** (max single-qubit entropy "
                f"{max_entropy:.3f} bits). Arrows are shorter than the sphere "
                "radius; the missing length is the entanglement."
            )
        else:
            st.success(
                "**Separable** (entropy ~ 0). Each qubit has its own pure state, "
                "so every arrow reaches the surface of its sphere."
            )

    columns = st.columns(min(n_qubits, 3))

    for qubit in range(n_qubits):
        # partial trace down to a single-qubit density matrix
        axis = n_qubits - 1 - qubit  # qubit 0 is the least significant index
        moved = np.moveaxis(tensor, axis, 0).reshape(2, -1)
        rho = moved @ moved.conj().T

        x = 2 * float(np.real(rho[0, 1]))
        y = 2 * float(np.imag(rho[1, 0]))
        z = float(np.real(rho[0, 0] - rho[1, 1]))
        purity = purities[qubit]
        entropy = entropies[qubit]
        length = float(np.sqrt(x * x + y * y + z * z))

        with columns[qubit % len(columns)]:
            figure = go.Figure()
            u, v = np.mgrid[0 : 2 * np.pi : 40j, 0 : np.pi : 20j]
            figure.add_surface(
                x=np.cos(u) * np.sin(v),
                y=np.sin(u) * np.sin(v),
                z=np.cos(v),
                opacity=0.18,
                colorscale=[[0, "#B2BEC3"], [1, "#B2BEC3"]],
                showscale=False,
                hoverinfo="skip",
            )
            if length < 0.02:
                # Zero vector: nothing to draw, so mark the centre explicitly
                # rather than rendering an empty sphere that reads as a bug.
                figure.add_trace(
                    go.Scatter3d(
                        x=[0],
                        y=[0],
                        z=[0],
                        mode="markers",
                        marker=dict(size=9, color="#E17055", symbol="x"),
                        hovertemplate=(
                            "Bloch vector is zero"
                            "<br>maximally mixed - fully entangled<extra></extra>"
                        ),
                    )
                )
            else:
                figure.add_trace(
                    go.Scatter3d(
                        x=[0, x],
                        y=[0, y],
                        z=[0, z],
                        mode="lines+markers",
                        line=dict(width=8, color="#E17055"),
                        marker=dict(size=[2, 7], color="#E17055"),
                        hovertemplate=f"({x:.3f}, {y:.3f}, {z:.3f})<extra></extra>",
                    )
                )
            if purity > 0.99:
                subtitle = "pure"
            else:
                subtitle = f"mixed | r={length:.2f} | S={entropy:.2f} bits"
            figure.update_layout(
                title=f"q{qubit}  ({subtitle})",
                margin=dict(l=0, r=0, t=30, b=0),
                height=280,
                scene=dict(
                    xaxis=dict(range=[-1, 1], title="X"),
                    yaxis=dict(range=[-1, 1], title="Y"),
                    zaxis=dict(range=[-1, 1], title="Z"),
                    aspectmode="cube",
                ),
                showlegend=False,
            )
            st.plotly_chart(figure, use_container_width=True)


# --------------------------------------------------------------------------- #
# Circuit diagram
# --------------------------------------------------------------------------- #
GATE_COLORS = {
    "h": "#6C5CE7",
    "x": "#E17055",
    "y": "#E84393",
    "z": "#0984E3",
    "s": "#00B894",
    "sdg": "#00B894",
    "t": "#00CEC9",
    "tdg": "#00CEC9",
    "sx": "#FDCB6E",
    "p": "#0984E3",
    "rx": "#D63031",
    "ry": "#E84393",
    "rz": "#0984E3",
    "id": "#B2BEC3",
    "swap": "#FD79A8",
}


def circuit_diagram(ir: dict[str, Any]) -> None:
    """Render the timeline as an SVG matching the composer grid."""
    n_qubits = int(ir.get("n_qubits", 1))
    ops = sorted(ir.get("ops", []), key=lambda o: o.get("layer", 0))
    n_layers = max((o.get("layer", 0) for o in ops), default=-1) + 1
    if n_layers == 0:
        st.info("Circuit is empty - drag gates from the palette to begin.")
        return

    cell, left, top = 58, 56, 26
    width = left + n_layers * cell + 24
    height = top + n_qubits * cell + 16

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
    ]

    for qubit in range(n_qubits):
        y = top + qubit * cell + cell / 2
        parts.append(
            f'<line x1="{left}" y1="{y}" x2="{width - 16}" y2="{y}" '
            'stroke="#2D3436" stroke-width="1.4"/>'
        )
        parts.append(
            f'<text x="12" y="{y + 5}" font-family="monospace" font-size="14" '
            f'fill="#2D3436">q[{qubit}]</text>'
        )

    for op in ops:
        layer = int(op.get("layer", 0))
        cx = left + layer * cell + cell / 2
        kind = op.get("kind")
        targets = op.get("qubits") or []
        controls = op.get("controls") or []

        if kind in {"if", "for", "while", "box"}:
            label = {
                "if": "IF",
                "for": "FOR",
                "while": "WHILE",
                "box": "BOX",
            }[kind]
            parts.append(
                f'<rect x="{cx - 24}" y="{top + 4}" width="48" '
                f'height="{n_qubits * cell - 8}" rx="8" fill="#DFE6E9" '
                'stroke="#636E72" stroke-dasharray="5,3"/>'
            )
            parts.append(
                f'<text x="{cx}" y="{top + 22}" text-anchor="middle" '
                f'font-family="sans-serif" font-size="11" font-weight="bold" '
                f'fill="#2D3436">{label}</text>'
            )
            continue

        involved = sorted(set(targets) | set(controls))
        if len(involved) > 1:
            y1 = top + involved[0] * cell + cell / 2
            y2 = top + involved[-1] * cell + cell / 2
            parts.append(
                f'<line x1="{cx}" y1="{y1}" x2="{cx}" y2="{y2}" '
                'stroke="#2D3436" stroke-width="2"/>'
            )

        for control in controls:
            y = top + control * cell + cell / 2
            parts.append(f'<circle cx="{cx}" cy="{y}" r="6" fill="#2D3436"/>')

        if kind == "measure":
            for qubit in targets:
                y = top + qubit * cell + cell / 2
                parts.append(
                    f'<rect x="{cx - 17}" y="{y - 17}" width="34" height="34" rx="5" '
                    'fill="#2D3436"/>'
                )
                parts.append(
                    f'<text x="{cx}" y="{y + 6}" text-anchor="middle" fill="#FFFFFF" '
                    'font-family="sans-serif" font-size="15">M</text>'
                )
            continue

        if kind == "reset":
            for qubit in targets:
                y = top + qubit * cell + cell / 2
                parts.append(
                    f'<rect x="{cx - 17}" y="{y - 17}" width="34" height="34" rx="5" '
                    'fill="#636E72"/>'
                )
                parts.append(
                    f'<text x="{cx}" y="{y + 6}" text-anchor="middle" fill="#FFFFFF" '
                    'font-family="sans-serif" font-size="12">|0></text>'
                )
            continue

        if kind == "barrier":
            for qubit in targets or range(n_qubits):
                y = top + qubit * cell
                parts.append(
                    f'<line x1="{cx}" y1="{y + 4}" x2="{cx}" y2="{y + cell - 4}" '
                    'stroke="#B2BEC3" stroke-width="3" stroke-dasharray="4,3"/>'
                )
            continue

        gate = (op.get("gate") or "").lower()
        params = op.get("params") or []
        label = gate.upper()
        if gate == "x" and controls:
            # draw CNOT-style target
            for qubit in targets:
                y = top + qubit * cell + cell / 2
                parts.append(
                    f'<circle cx="{cx}" cy="{y}" r="14" fill="#FFFFFF" '
                    'stroke="#2D3436" stroke-width="2"/>'
                )
                parts.append(
                    f'<line x1="{cx - 14}" y1="{y}" x2="{cx + 14}" y2="{y}" '
                    'stroke="#2D3436" stroke-width="2"/>'
                )
                parts.append(
                    f'<line x1="{cx}" y1="{y - 14}" x2="{cx}" y2="{y + 14}" '
                    'stroke="#2D3436" stroke-width="2"/>'
                )
            continue

        if gate == "swap":
            for qubit in targets:
                y = top + qubit * cell + cell / 2
                parts.append(
                    f'<line x1="{cx - 9}" y1="{y - 9}" x2="{cx + 9}" y2="{y + 9}" '
                    'stroke="#2D3436" stroke-width="2.5"/>'
                )
                parts.append(
                    f'<line x1="{cx - 9}" y1="{y + 9}" x2="{cx + 9}" y2="{y - 9}" '
                    'stroke="#2D3436" stroke-width="2.5"/>'
                )
            continue

        color = GATE_COLORS.get(gate, "#6C5CE7")
        if params:
            label = f"{gate.upper()}({params[0].get('expr', '')})"
        box_width = max(34, 9 * len(label))
        for qubit in targets:
            y = top + qubit * cell + cell / 2
            parts.append(
                f'<rect x="{cx - box_width / 2}" y="{y - 17}" width="{box_width}" '
                f'height="34" rx="5" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{cx}" y="{y + 6}" text-anchor="middle" fill="#FFFFFF" '
                f'font-family="sans-serif" font-size="13" font-weight="600">{label}</text>'
            )

    parts.append("</svg>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def backend_badge(result: dict[str, Any]) -> None:
    metadata = result.get("metadata") or {}
    columns = st.columns(4)
    columns[0].metric("Backend", metadata.get("engine") or metadata.get("backend", "-"))
    columns[1].metric("Shots", metadata.get("shots", "-"))
    columns[2].metric("Qubits", metadata.get("n_qubits", "-"))
    columns[3].metric("Runtime", f"{metadata.get('runtime_seconds', 0):.3f}s")
    for warning in metadata.get("warnings") or []:
        st.caption(f":warning: {warning}")


# --------------------------------------------------------------------------- #
# Gauges / meters
# --------------------------------------------------------------------------- #
TEAL = "#3dd6c6"
GOLD = "#ffd166"
CORAL = "#ff5d5d"
MUTED = "#8b9bb4"


def gauge(
    value: float,
    title: str,
    *,
    subtitle: str = "",
    color: str = TEAL,
    vmax: float = 1.0,
) -> go.Figure:
    """A single dial. Kept small so several sit side by side."""
    heading = (
        f"<span style='font-size:17px'>{title}</span>"
        f"<br><span style='font-size:12px;color:{MUTED}'>{subtitle}</span>"
    )
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(value),
            number={"valueformat": ".3f", "font": {"size": 34}},
            title={"text": heading, "font": {"size": 16}},
            domain={"x": [0.05, 0.95], "y": [0.0, 0.72]},
            gauge={
                "axis": {"range": [0, vmax], "tickcolor": MUTED},
                "bar": {"color": color, "thickness": 0.32},
                "bgcolor": "#1b2030",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, vmax * 0.33], "color": "#18202c"},
                    {"range": [vmax * 0.33, vmax * 0.66], "color": "#1e2a3c"},
                    {"range": [vmax * 0.66, vmax], "color": "#24344c"},
                ],
            },
        )
    )
    figure.update_layout(height=250, margin=dict(l=10, r=10, t=60, b=4))
    return figure


def metric_meters(result: dict[str, Any]) -> None:
    """Entanglement / fidelity / purity dials, mirroring the reference app."""
    metadata = result.get("metadata") or {}
    metrics = metadata.get("metrics") or {}
    if not metrics:
        return
    noisy = bool((metadata.get("noise") or {}).get("enabled"))

    entropy = float(metrics.get("entanglement_entropy", 0.0))
    concurrence = metrics.get("concurrence")
    entangled = bool(metrics.get("entangled"))

    columns = st.columns(3)
    with columns[0]:
        subtitle = "ENTANGLED" if entangled else "separable"
        if concurrence is not None:
            subtitle += f"  |  C={float(concurrence):.2f}"
        st.plotly_chart(
            gauge(
                entropy,
                "Entanglement S",
                subtitle=subtitle,
                color=GOLD if entangled else TEAL,
            ),
            use_container_width=True,
        )
    with columns[1]:
        if "fidelity" in metrics:
            fidelity = float(metrics["fidelity"])
            color = TEAL if fidelity > 0.97 else GOLD if fidelity > 0.85 else CORAL
            st.plotly_chart(
                gauge(
                    fidelity,
                    "Fidelity",
                    subtitle="F(ideal, noisy rho)" if noisy else "no noise applied",
                    color=color,
                ),
                use_container_width=True,
            )
    with columns[2]:
        if "purity" in metrics:
            purity = float(metrics["purity"])
            color = TEAL if purity > 0.97 else GOLD if purity > 0.85 else CORAL
            st.plotly_chart(
                gauge(
                    purity,
                    "Purity",
                    subtitle="Tr(rho^2)  |  1 = still pure",
                    color=color,
                ),
                use_container_width=True,
            )

    if noisy:
        cols = st.columns(2)
        cols[0].metric("TV distance (ideal vs noisy)", f"{metrics.get('total_variation', 0.0):.3f}")
        cols[1].metric("Shot leakage", f"{metrics.get('shot_leakage', 0.0) * 100:.1f}%")


def ideal_vs_noisy(result: dict[str, Any]) -> None:
    """Grouped ideal/noisy histogram plus the per-state difference."""
    metadata = result.get("metadata") or {}
    ideal_counts = metadata.get("ideal_counts")
    if not ideal_counts:
        st.info(
            "Enable the noise model on the Qiskit Aer backend to compare an "
            "ideal run against a noisy one."
        )
        return

    noisy_counts = result.get("counts") or {}
    total_ideal = sum(ideal_counts.values()) or 1
    total_noisy = sum(noisy_counts.values()) or 1
    labels = sorted(set(ideal_counts) | set(noisy_counts))
    ideal = [ideal_counts.get(k, 0) / total_ideal for k in labels]
    noisy = [noisy_counts.get(k, 0) / total_noisy for k in labels]

    figure = go.Figure()
    figure.add_bar(name="Ideal", x=labels, y=ideal, marker_color=TEAL)
    figure.add_bar(name="Noisy", x=labels, y=noisy, marker_color=CORAL)
    figure.update_layout(
        barmode="group",
        height=400,
        xaxis_title="Basis state (qubit 0 = rightmost)",
        yaxis_title="Probability",
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    figure.update_xaxes(type="category")
    st.plotly_chart(figure, use_container_width=True)

    delta = go.Figure(
        go.Bar(
            x=labels,
            y=[n - i for i, n in zip(ideal, noisy)],
            marker_color=[CORAL if n - i > 0 else TEAL for i, n in zip(ideal, noisy)],
        )
    )
    delta.update_layout(
        height=280,
        title="Noisy minus ideal (positive = noise added weight here)",
        xaxis_title="Basis state",
        yaxis_title="Probability difference",
        margin=dict(l=10, r=10, t=50, b=10),
    )
    delta.update_xaxes(type="category")
    st.plotly_chart(delta, use_container_width=True)


def born_vs_shots(result: dict[str, Any]) -> None:
    """Exact |amplitude|^2 against the sampled counts.

    This isolates *sampling* error, which students routinely confuse with
    hardware noise: a finite number of shots never reproduces the exact
    distribution even on a perfect simulator.
    """
    amplitudes = _amplitudes(result)
    counts = result.get("counts") or {}
    if amplitudes is None or not counts:
        st.info("Needs both a statevector and measurement counts.")
        return

    n_qubits = int(math.log2(len(amplitudes)))
    exact = {
        format(i, f"0{n_qubits}b"): float(abs(a) ** 2)
        for i, a in enumerate(amplitudes)
        if abs(a) ** 2 > 1e-12
    }
    total = sum(counts.values()) or 1
    sampled = {k: v / total for k, v in counts.items()}
    labels = sorted(set(exact) | set(sampled))

    figure = go.Figure()
    figure.add_bar(
        name="exact |psi|^2", x=labels, y=[exact.get(k, 0.0) for k in labels],
        marker_color=TEAL,
    )
    figure.add_bar(
        name=f"{total} shots", x=labels, y=[sampled.get(k, 0.0) for k in labels],
        marker_color="#6C5CE7",
    )
    figure.update_layout(
        barmode="group",
        height=380,
        xaxis_title="Basis state",
        yaxis_title="Probability",
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    figure.update_xaxes(type="category")
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Gaps here are **sampling error** from a finite shot count, not "
        "hardware noise. Raise the shots and the two bars converge."
    )


def density_matrix(result: dict[str, Any]) -> None:
    """Heatmap of |rho| for the ideal state."""
    amplitudes = _amplitudes(result)
    if amplitudes is None:
        st.info("Density matrix needs a statevector.")
        return
    n_qubits = int(math.log2(len(amplitudes)))
    if n_qubits > 5:
        st.info("Density matrix view is limited to 5 qubits.")
        return

    rho = np.outer(amplitudes, amplitudes.conj())
    labels = [f"|{format(i, f'0{n_qubits}b')}>" for i in range(len(amplitudes))]
    figure = go.Figure(
        go.Heatmap(
            z=np.abs(rho),
            x=labels,
            y=labels,
            colorscale="Viridis",
            zmin=0,
            zmax=max(1.0, float(np.abs(rho).max())),
            colorbar=dict(title="|rho|"),
            hovertemplate="row %{y}<br>col %{x}<br>|rho|=%{z:.3f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=440,
        yaxis=dict(autorange="reversed", title="bra", scaleanchor="x"),
        xaxis=dict(title="ket", side="top"),
        margin=dict(l=60, r=40, t=60, b=30),
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Ideal |rho|. A Bell state lights up the off-diagonal |00><11| corners "
        "-- those corners ARE the entanglement. A classical mixture would show "
        "only the diagonal."
    )


def phase_table(result: dict[str, Any]) -> None:
    """Amplitude and relative phase per basis state."""
    amplitudes = _amplitudes(result)
    if amplitudes is None:
        st.info("Phase table needs a statevector.")
        return
    n_qubits = int(math.log2(len(amplitudes)))
    relative = _relative_phases(amplitudes)
    rows = []
    for index, amplitude in enumerate(amplitudes):
        probability = float(abs(amplitude) ** 2)
        if probability <= 1e-10:
            continue
        rows.append(
            {
                "State": f"|{format(index, f'0{n_qubits}b')}>",
                "Re": round(float(amplitude.real), 6),
                "Im": round(float(amplitude.imag), 6),
                "Probability": round(probability, 6),
                "Percent": round(probability * 100, 3),
                "Rel. phase (rad)": round(float(relative[index]), 6),
                "Rel. phase (deg)": round(float(np.degrees(relative[index])), 2),
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(
            "Phases are **relative** to the first populated state; a global "
            "phase is physically unobservable."
        )
