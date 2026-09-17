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

// Safety net. If Streamlit's RENDER event is missed, the wrapper renders null
// and the user is left staring at an empty white box with no clue why.
// Re-announce readiness; Streamlit replies with a fresh RENDER event, which
// unblocks the component.
//
// This watches forever rather than giving up after a few tries. Streamlit
// destroys and recreates the iframe whenever the number of elements above the
// component changes -- pressing "Build / refresh timeline" adds four transport
// buttons and a table above it -- so a component that rendered fine a moment
// ago can be torn down and come back blank at any point in the session. The
// check is a single childElementCount read, so polling is essentially free.
const rootEl = document.getElementById("root")!
let blankTicks = 0
window.setInterval(() => {
  if (rootEl.childElementCount > 0) {
    blankTicks = 0
    return
  }
  blankTicks += 1
  if (blankTicks >= 2) {
    // Rebuild the React root as well as re-announcing readiness. If the DOM
    // was emptied underneath React, its virtual tree still believes the
    // content is mounted and a fresh RENDER event alone repaints nothing.
    // The component is alive but has no renderData, so it is painting null.
    // Re-announcing readiness makes Streamlit send a fresh RENDER event, which
    // is what actually unblocks it. Do not tear down the React root here:
    // rebuilding it while Streamlit still owns the iframe throws and leaves
    // the box blank for good.
    Streamlit.setComponentReady()
    Streamlit.setFrameHeight()
    blankTicks = 0
  }
}, 500)
