# Two-stage by design, mirroring how the frozen Streamlit stack treats its
# composer bundle: the image carries a working build so a fresh clone can
# `make up` with no host Node.
#
# NOTE: the build CONTEXT is ./frontend (sibling of this folder), not
# ./frontend/web, because the drag-and-drop grid is shared with the Streamlit
# component that owns it (see the @composer alias in vite.config.ts). Both
# apps compile the same source, so the two UIs can never drift.
#
#   docker build -f web/Dockerfile .     # from ./frontend

FROM node:22-alpine AS build
WORKDIR /build

COPY web/package.json web/package-lock.json ./web/
RUN cd web && npm ci --no-audit --no-fund

COPY web ./web
# Shared with the Streamlit component; keep in step with vite.config.ts.
COPY circuit_composer/frontend/src ./circuit_composer/frontend/src

RUN cd web && npm run build

FROM nginx:1.27-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/web/dist /usr/share/nginx/html
EXPOSE 80
