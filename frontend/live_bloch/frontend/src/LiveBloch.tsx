/**
 * Continuous Bloch sphere explorer.
 *
 * Everything recomputes locally on every pointer move, so dragging a slider or
 * spinning the sphere is immediate. Streamlit is told the final state only
 * after the user pauses, which keeps the page from rerunning mid-gesture.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  ComponentProps,
  Streamlit,
  withStreamlitConnection,
} from "streamlit-component-lib"
import Sphere from "./Sphere"
import {
  GATES,
  GATE_HELP,
  LANDMARKS,
  applyGates,
  blochAngles,
  blochVector,
  ketString,
  probabilities,
  stateFromAngles,
} from "./quantum"

const COMMIT_DELAY_MS = 400

function LiveBlochInner({ args, theme }: ComponentProps) {
  const [theta, setTheta] = useState<number>(args["theta"] ?? 90)
  const [phi, setPhi] = useState<number>(args["phi"] ?? 0)
  const [gates, setGates] = useState<string[]>(args["gates"] ?? [])
  const rootRef = useRef<HTMLDivElement>(null)
  const dark = theme?.base === "dark"

  const base = useMemo(() => stateFromAngles(theta, phi), [theta, phi])
  const state = useMemo(() => applyGates(base, gates), [base, gates])
  const vector = useMemo(() => blochVector(state), [state])
  const [p0, p1] = probabilities(state)
  const [outTheta, outPhi] = blochAngles(state)

  // Trail: where each gate in the sequence takes the state, so a rotation is
  // visible rather than just a jump.
  const trail = useMemo(() => {
    const points: [number, number, number][] = [blochVector(base)]
    let current = base
    for (const gate of gates) {
      current = applyGates(current, [gate])
      points.push(blochVector(current))
    }
    return points
  }, [base, gates])

  useEffect(() => {
    document.body.classList.toggle("dark", dark)
  }, [dark])

  const resize = useCallback(() => {
    const measured = Math.max(
      document.body?.scrollHeight ?? 0,
      rootRef.current?.scrollHeight ?? 0,
    )
    // Never report 0: Streamlit would collapse the iframe and the component
    // would look like a blank white box with no console error.
    Streamlit.setFrameHeight(Math.max(measured, 430))
  }, [])

  useEffect(() => {
    resize()
    const raf = requestAnimationFrame(resize)
    return () => cancelAnimationFrame(raf)
  })

  // Report to Python only after the gesture settles. Every setComponentValue
  // triggers a full page rerun, so committing per pointer move would undo the
  // whole point of this component.
  useEffect(() => {
    const id = window.setTimeout(() => {
      Streamlit.setComponentValue({
        theta: outTheta, phi: outPhi, gates,
        p0, p1,
        amplitudes: [
          [state[0].re, state[0].im],
          [state[1].re, state[1].im],
        ],
      })
    }, COMMIT_DELAY_MS)
    return () => window.clearTimeout(id)
  }, [outTheta, outPhi, gates, p0, p1, state])

  const toggleGate = (name: string) =>
    setGates((prev) =>
      prev.includes(name) && prev[prev.length - 1] === name
        ? prev.slice(0, -1)
        : [...prev, name],
    )

  return (
    <div className="lb" ref={rootRef}>
      <div className="lb-grid">
        <div className="lb-sphere">
          <Sphere
            vector={vector}
            dark={dark}
            trail={trail}
            onPick={(t, p) => {
              setTheta(t)
              setPhi(p)
              setGates([])
            }}
          />
        </div>

        <div className="lb-panel">
          <label className="lb-label">
            θ <span className="lb-value">{theta.toFixed(0)}°</span>
          </label>
          <input
            className="lb-slider" type="range" min={0} max={180} step={1}
            value={theta} onChange={(e) => setTheta(Number(e.target.value))}
          />

          <label className="lb-label">
            φ <span className="lb-value">{phi.toFixed(0)}°</span>
          </label>
          <input
            className="lb-slider" type="range" min={0} max={360} step={1}
            value={phi} onChange={(e) => setPhi(Number(e.target.value))}
          />

          <div className="lb-section">Jump to</div>
          <div className="lb-chips">
            {Object.entries(LANDMARKS).map(([name, [t, p]]) => (
              <button
                key={name} className="lb-chip"
                onClick={() => { setTheta(t); setPhi(p); setGates([]) }}
              >
                {name}
              </button>
            ))}
          </div>

          <div className="lb-section">Apply a gate</div>
          <div className="lb-chips">
            {Object.keys(GATES).map((name) => (
              <button
                key={name} className="lb-chip lb-gate" title={GATE_HELP[name]}
                onClick={() => toggleGate(name)}
              >
                {name}
              </button>
            ))}
            {gates.length > 0 && (
              <button className="lb-chip lb-clear" onClick={() => setGates([])}>
                clear
              </button>
            )}
          </div>
          {gates.length > 0 && (
            <div className="lb-wire">|ψ⟩ ── {gates.join(" ── ")}</div>
          )}

          <div className="lb-state">{ketString(state)}</div>

          <div className="lb-bars">
            <div className="lb-bar-row">
              <span>P(0)</span>
              <div className="lb-bar"><div style={{ width: `${p0 * 100}%` }} /></div>
              <span className="lb-pct">{(p0 * 100).toFixed(1)}%</span>
            </div>
            <div className="lb-bar-row">
              <span>P(1)</span>
              <div className="lb-bar"><div style={{ width: `${p1 * 100}%` }} /></div>
              <span className="lb-pct">{(p1 * 100).toFixed(1)}%</span>
            </div>
          </div>

          <div className="lb-readout">
            θ = {outTheta.toFixed(1)}° · φ = {outPhi.toFixed(1)}° · |r| ={" "}
            {Math.hypot(...vector).toFixed(3)}
          </div>
        </div>
      </div>
    </div>
  )
}

export default withStreamlitConnection(LiveBlochInner)
