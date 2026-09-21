import ReactDOM from "react-dom/client"
import { Streamlit } from "streamlit-component-lib"
import LiveBloch from "./LiveBloch"
import "./styles.css"

// streamlit-component-lib calls setFrameHeight() with no argument, which
// defaults to document.body.scrollHeight. Before layout settles that is 0,
// Streamlit collapses the iframe, and the component renders as a blank white
// box with no console error. Clamp every height that goes out.
const MIN_FRAME_HEIGHT = 430
const original = Streamlit.setFrameHeight.bind(Streamlit)
Streamlit.setFrameHeight = (height?: number) => {
  const measured =
    height ??
    Math.max(document.body?.scrollHeight ?? 0, document.documentElement?.scrollHeight ?? 0)
  original(Math.max(measured, MIN_FRAME_HEIGHT))
}

// Deliberately NOT wrapped in React.StrictMode. StrictMode double-mounts, and
// withStreamlitConnection tears down its RENDER listener on unmount; if
// Streamlit's one-shot render lands in that gap the iframe stays blank.
ReactDOM.createRoot(document.getElementById("root")!).render(<LiveBloch />)

// Watchdog: if the component is ever blank, re-announce readiness so
// Streamlit sends a fresh render event.
const rootEl = document.getElementById("root")!
let blankTicks = 0
window.setInterval(() => {
  if (rootEl.childElementCount > 0) { blankTicks = 0; return }
  blankTicks += 1
  if (blankTicks >= 2) {
    Streamlit.setComponentReady()
    Streamlit.setFrameHeight()
    blankTicks = 0
  }
}, 500)
