import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The browser only ever calls /api/*; the proxy (nginx in compose, Vite here)
// strips /api and forwards to the FastAPI root, so the SPA is same-origin in
// every environment and CORS never enters the picture in the served stack.
//
// Vite refuses Host headers it does not recognise, which blocks hosted preview
// URLs. That is a good default for a dev server, so it stays: set
// VITE_ALLOWED_HOSTS=host1,host2 to serve from a sandbox or a LAN name.
// Production is served by nginx, which performs no such check.
const allowedHosts = process.env.VITE_ALLOWED_HOSTS
  ? process.env.VITE_ALLOWED_HOSTS.split(",").map((h) => h.trim())
  : undefined;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 3001,
    strictPort: true,
    allowedHosts,
    watch: { usePolling: true },
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 3001,
    proxy: {
      "/api": {
        target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
