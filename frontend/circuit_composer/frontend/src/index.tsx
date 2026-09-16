import ReactDOM from "react-dom/client"
import { Streamlit } from "streamlit-component-lib"
import Composer from "./Composer"
import "./styles.css"

// streamlit-component-lib calls Streamlit.setFrameHeight() with no argument on
// mount and after every render. It defaults to document.body.scrollHeight,
// which is 0 before layout settles -- Streamlit then collapses the iframe and
// the composer shows as a blank white box with nothing in the console. Clamp
// every height that goes out, including the library's own calls.
const MIN_FRAME_HEIGHT = 560
const originalSetFrameHeight = Streamlit.setFrameHeight.bind(Streamlit)
Streamlit.setFrameHeight = (height?: number) => {
  const measured =
    height ??
    Math.max(
      document.body?.scrollHeight ?? 0,
      document.documentElement?.scrollHeight ?? 0,
    )
  originalSetFrameHeight(Math.max(measured, MIN_FRAME_HEIGHT))
}

// NOTE: deliberately NOT wrapped in React.StrictMode.
//
// withStreamlitConnection registers its RENDER_EVENT listener in
// componentDidMount and tears it down in componentWillUnmount, then signals
// readiness with Streamlit.setComponentReady(). StrictMode mounts, unmounts and
// remounts every component, so the listener can be removed exactly while
// Streamlit is delivering its one and only RENDER event. When that happens
// renderData stays null forever, the wrapper returns null, and the component is
// a permanently blank white iframe with no error in the console.
ReactDOM.createRoot(document.getElementById("root")!).render(<Composer />)

// Safety net. If Streamlit's RENDER event is somehow missed, the wrapper
// renders null and the user is left staring at an empty white box with no clue
// why. Re-announce readiness a few times; Streamlit replies with a fresh RENDER
// event, which unblocks the component. Stops as soon as anything is drawn.
const root = document.getElementById("root")!
let attempts = 0
const retry = window.setInterval(() => {
  if (root.childElementCount > 0 || attempts >= 5) {
    window.clearInterval(retry)
    return
  }
  attempts += 1
  Streamlit.setComponentReady()
  Streamlit.setFrameHeight()
}, 400)
