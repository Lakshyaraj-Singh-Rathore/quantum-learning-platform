import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// Streamlit serves the component from a nested path, so assets must be relative.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "build",
    emptyOutDir: true,
  },
  server: { port: 3001 },
})
