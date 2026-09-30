import { Streamlit, StreamlitComponentBase, withStreamlitConnection } from "streamlit-component-lib"
import type { ComponentProps } from "streamlit-component-lib"
import type { CircuitIR } from "./types"
import { ComposerInner } from "./Composer"

/**
 * Streamlit host adapter for the composer grid.
 *
 * All of the iframe-specific behaviour lives here: reading the circuit out of
 * `args`, pushing edits back with setComponentValue, and reporting height with
 * setFrameHeight. `Composer.tsx` itself knows nothing about Streamlit, which is
 * what lets the new React SPA (frontend/web) mount the same grid from props.
 */
class StreamlitComposer extends StreamlitComponentBase {
  public render() {
    const props = this.props as ComponentProps
    return (
      <ComposerInner
        value={(props.args["value"] ?? null) as CircuitIR | null}
        nQubits={(props.args["nQubits"] as number | undefined) ?? undefined}
        theme={{ base: props.theme?.base as string | undefined }}
        onChange={(ir) => Streamlit.setComponentValue(ir)}
        onHeight={(height) => Streamlit.setFrameHeight(height)}
      />
    )
  }
}

export default withStreamlitConnection(StreamlitComposer)
