/**
 * A Bloch sphere drawn on a canvas, rotatable by dragging.
 *
 * Canvas rather than SVG or Plotly because this redraws on every pointer move;
 * a React tree of a few hundred SVG nodes would stutter. The projection is a
 * simple orthographic camera, which is all a unit sphere needs.
 */

import { useCallback, useEffect, useRef } from "react"

type Props = {
  vector: [number, number, number]
  dark: boolean
  /** Clicking the sphere reports the (theta, phi) picked, in degrees. */
  onPick?: (theta: number, phi: number) => void
  trail?: [number, number, number][]
}

const SIZE = 300
const R = 115

export default function Sphere({ vector, dark, onPick, trail = [] }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  // Camera angles live in a ref, not state: a re-render per mousemove is
  // exactly the cost this component exists to avoid.
  const cam = useRef({ yaw: -0.6, pitch: 0.45 })
  const dragging = useRef(false)
  const moved = useRef(false)
  const last = useRef({ x: 0, y: 0 })

  const project = useCallback((x: number, y: number, z: number) => {
    const { yaw, pitch } = cam.current
    // Rotate about Z (yaw) then about the camera's X axis (pitch).
    const x1 = x * Math.cos(yaw) - y * Math.sin(yaw)
    const y1 = x * Math.sin(yaw) + y * Math.cos(yaw)
    const y2 = y1 * Math.cos(pitch) - z * Math.sin(pitch)
    const z2 = y1 * Math.sin(pitch) + z * Math.cos(pitch)
    return { sx: SIZE / 2 + x1 * R, sy: SIZE / 2 - z2 * R, depth: y2 }
  }, [])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const fg = dark ? "#e6edf3" : "#1c2128"
    const grid = dark ? "rgba(160,174,192,0.40)" : "rgba(90,100,115,0.35)"
    const accent = "#e17055"

    ctx.clearRect(0, 0, SIZE, SIZE)

    // Sphere body.
    ctx.beginPath()
    ctx.arc(SIZE / 2, SIZE / 2, R, 0, Math.PI * 2)
    ctx.fillStyle = dark ? "rgba(140,155,175,0.10)" : "rgba(120,135,155,0.10)"
    ctx.fill()
    ctx.strokeStyle = grid
    ctx.lineWidth = 1
    ctx.stroke()

    // Great circles: equator and the two meridians. Without them the eye has
    // nothing to judge direction against.
    const circles: [number, number, number][][] = [[], [], []]
    for (let i = 0; i <= 120; i++) {
      const t = (i / 120) * Math.PI * 2
      circles[0].push([Math.cos(t), Math.sin(t), 0])
      circles[1].push([Math.cos(t), 0, Math.sin(t)])
      circles[2].push([0, Math.cos(t), Math.sin(t)])
    }
    for (const circle of circles) {
      ctx.beginPath()
      circle.forEach(([x, y, z], i) => {
        const p = project(x, y, z)
        // Fade the far half so the sphere reads as three-dimensional.
        ctx.globalAlpha = p.depth > 0 ? 0.25 : 0.75
        if (i === 0) ctx.moveTo(p.sx, p.sy)
        else ctx.lineTo(p.sx, p.sy)
      })
      ctx.strokeStyle = grid
      ctx.stroke()
      ctx.globalAlpha = 1
    }

    // Axis labels at the six cardinal states.
    const labels: [string, [number, number, number]][] = [
      ["|0⟩", [0, 0, 1.22]], ["|1⟩", [0, 0, -1.22]],
      ["|+⟩", [1.22, 0, 0]], ["|−⟩", [-1.22, 0, 0]],
      ["|+i⟩", [0, 1.22, 0]], ["|−i⟩", [0, -1.22, 0]],
    ]
    ctx.font = "11px system-ui, sans-serif"
    ctx.fillStyle = dark ? "#8899a6" : "#5a6472"
    ctx.textAlign = "center"
    ctx.textBaseline = "middle"
    for (const [text, [x, y, z]] of labels) {
      const p = project(x, y, z)
      ctx.globalAlpha = p.depth > 0 ? 0.45 : 1
      ctx.fillText(text, p.sx, p.sy)
    }
    ctx.globalAlpha = 1

    // Where the state has been, so a gate's rotation is visible.
    if (trail.length > 1) {
      ctx.beginPath()
      trail.forEach(([x, y, z], i) => {
        const p = project(x, y, z)
        if (i === 0) ctx.moveTo(p.sx, p.sy)
        else ctx.lineTo(p.sx, p.sy)
      })
      ctx.strokeStyle = "rgba(225,112,85,0.35)"
      ctx.lineWidth = 2
      ctx.stroke()
    }

    // The state vector.
    const [vx, vy, vz] = vector
    const length = Math.hypot(vx, vy, vz)
    const origin = project(0, 0, 0)
    if (length > 0.02) {
      const tip = project(vx, vy, vz)
      // Dotted drop line to the equatorial plane resolves the usual 3D
      // ambiguity between "up" and "towards the viewer".
      const foot = project(vx, vy, 0)
      ctx.setLineDash([3, 3])
      ctx.beginPath()
      ctx.moveTo(tip.sx, tip.sy)
      ctx.lineTo(foot.sx, foot.sy)
      ctx.lineTo(origin.sx, origin.sy)
      ctx.strokeStyle = "rgba(225,112,85,0.45)"
      ctx.lineWidth = 1.5
      ctx.stroke()
      ctx.setLineDash([])

      ctx.beginPath()
      ctx.moveTo(origin.sx, origin.sy)
      ctx.lineTo(tip.sx, tip.sy)
      ctx.strokeStyle = accent
      ctx.lineWidth = 3
      ctx.stroke()

      ctx.beginPath()
      ctx.arc(tip.sx, tip.sy, 6, 0, Math.PI * 2)
      ctx.fillStyle = accent
      ctx.fill()
    } else {
      // Zero vector: a maximally mixed qubit has no direction at all.
      ctx.beginPath()
      ctx.arc(origin.sx, origin.sy, 6, 0, Math.PI * 2)
      ctx.strokeStyle = accent
      ctx.lineWidth = 2
      ctx.stroke()
    }

    ctx.fillStyle = fg
    ctx.font = "10px system-ui, sans-serif"
    ctx.textAlign = "left"
    ctx.fillText("drag to rotate · click to set the state", 8, SIZE - 8)
  }, [vector, dark, project, trail])

  useEffect(() => {
    draw()
  }, [draw])

  const onDown = (event: React.PointerEvent) => {
    dragging.current = true
    moved.current = false
    last.current = { x: event.clientX, y: event.clientY }
    ;(event.target as HTMLElement).setPointerCapture(event.pointerId)
  }

  const onMove = (event: React.PointerEvent) => {
    if (!dragging.current) return
    const dx = event.clientX - last.current.x
    const dy = event.clientY - last.current.y
    if (Math.abs(dx) + Math.abs(dy) > 2) moved.current = true
    last.current = { x: event.clientX, y: event.clientY }
    cam.current.yaw += dx * 0.01
    cam.current.pitch = Math.max(
      -1.4, Math.min(1.4, cam.current.pitch + dy * 0.01),
    )
    draw()  // redraw directly; no React render, so this stays smooth
  }

  const onUp = (event: React.PointerEvent) => {
    dragging.current = false
    if (moved.current || !onPick) return
    // A click (not a drag) picks the nearest point on the sphere surface.
    const rect = (event.target as HTMLElement).getBoundingClientRect()
    const px = (event.clientX - rect.left - SIZE / 2) / R
    const py = -(event.clientY - rect.top - SIZE / 2) / R
    if (Math.hypot(px, py) > 1) return
    // Invert the projection on the near hemisphere (depth <= 0).
    const { yaw, pitch } = cam.current
    const z2 = py
    const depth = -Math.sqrt(Math.max(0, 1 - px * px - py * py))
    const y1 = z2 * Math.sin(pitch) + depth * Math.cos(pitch)
    const z = z2 * Math.cos(pitch) - depth * Math.sin(pitch)
    const x1 = px
    const x = x1 * Math.cos(yaw) + y1 * Math.sin(yaw)
    const y = -x1 * Math.sin(yaw) + y1 * Math.cos(yaw)
    const theta = (Math.acos(Math.min(1, Math.max(-1, z))) * 180) / Math.PI
    const phi = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360
    onPick(theta, phi)
  }

  return (
    <canvas
      ref={canvasRef}
      width={SIZE}
      height={SIZE}
      style={{ touchAction: "none", cursor: dragging.current ? "grabbing" : "grab" }}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
    />
  )
}
