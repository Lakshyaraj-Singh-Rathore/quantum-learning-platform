import React from "react"
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

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Composer />
  </React.StrictMode>,
)
