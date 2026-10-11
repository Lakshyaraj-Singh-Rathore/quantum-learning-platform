import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

// The drag-and-drop grid lives in frontend/circuit_composer and is compiled
// from source into this app, so there is exactly one copy of it. It is
// aliased rather than moved because that directory is where the grid's own
// history and tests live; the alias is the single seam between the two trees
// (see scripts/link-shared.mjs, which makes `react` resolve here).
//
// The paths are absolute so they resolve identically on a dev host and inside
// the image, where the build context is ./frontend and the two trees sit side
// by side (see frontend/web/Dockerfile).
const composerSrc = fileURLToPath(
  new URL("../circuit_composer/frontend/src", import.meta.url),
);
const frontendRoot = fileURLToPath(new URL("..", import.meta.url));

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
  resolve: {
    alias: { "@composer": composerSrc },
    // The grid's source lives outside this app, in a directory that gets its
    // own node_modules when it has been installed locally. Without dedupe,
    // `react` imported from there resolves to that second copy and the bundle
    // ships two Reacts — which fails at runtime with "invalid hook"
    // call", not at build time. One React, resolved from this app.
    dedupe: ["react", "react-dom"],
  },
  server: {
    host: "0.0.0.0",
    port: 3001,
    strictPort: true,
    allowedHosts,
    // The grid's source sits outside this app's root, so Vite (dev) must be
    // told it is allowed to serve it.
    fs: { allow: [frontendRoot] },
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
    // `preview` does not inherit `server.allowedHosts`. Without this the built
    // bundle 403s every hosted preview URL while the dev server serves the same
    // host happily, which is a confusing way to discover the two are separate.
    allowedHosts,
    strictPort: true,
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
