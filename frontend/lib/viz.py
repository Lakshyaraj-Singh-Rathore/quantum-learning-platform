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
def histogram(result: dict[str, Any]) -> None:
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
    values = [v for _, v in items]

    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            text=[f"{v}<br>{v / total:.1%}" for v in values],
            textposition="outside",
            marker_color="#6C5CE7",
            hovertemplate="<b>%{x}</b><br>count %{y}<extra></extra>",
        )
    )
    figure.update_layout(
        xaxis_title="Bitstring (qubit 0 = rightmost)",
        yaxis_title="Counts",
        margin=dict(l=10, r=10, t=30, b=10),
        height=360,
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)
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


def phase_disk(result: dict[str, Any]) -> None:
    """Phase disk: magnitude as radius, relative phase as angle, per basis state."""
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
    if len(indices) > 64:
        indices = indices[np.argsort(probabilities[indices])[::-1][:64]]

    angles = np.angle(amplitudes[indices])
    radii = np.abs(amplitudes[indices])
    labels = [format(int(i), f"0{n_qubits}b") for i in indices]

    figure = go.Figure(
        go.Scatterpolar(
            r=radii,
            theta=np.degrees(angles),
            mode="markers+text",
            text=labels,
            textposition="top center",
            marker=dict(
                size=14,
                color=np.degrees(angles),
                colorscale="HSV",
                cmin=-180,
                cmax=180,
                showscale=True,
                colorbar=dict(title="Phase (deg)"),
            ),
            hovertemplate="<b>|%{text}></b><br>|amp| %{r:.4f}<br>phase %{theta:.1f}deg<extra></extra>",
        )
    )
    figure.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, max(1.0, float(radii.max()) * 1.15)], title="|amplitude|"),
            angularaxis=dict(direction="counterclockwise"),
        ),
        margin=dict(l=30, r=30, t=30, b=30),
        height=420,
        showlegend=False,
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Distance from the centre is the amplitude magnitude; the angle is the relative "
        "phase. States with equal probability but different phase sit at the same radius "
        "and different angles."
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
    columns = st.columns(min(n_qubits, 3))

    for qubit in range(n_qubits):
        # partial trace down to a single-qubit density matrix
        axis = n_qubits - 1 - qubit  # qubit 0 is the least significant index
        moved = np.moveaxis(tensor, axis, 0).reshape(2, -1)
        rho = moved @ moved.conj().T

        x = 2 * float(np.real(rho[0, 1]))
        y = 2 * float(np.imag(rho[1, 0]))
        z = float(np.real(rho[0, 0] - rho[1, 1]))
        purity = float(np.real(np.trace(rho @ rho)))

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
            figure.update_layout(
                title=f"q{qubit}" + ("" if purity > 0.99 else f" (mixed, purity {purity:.2f})"),
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
