# Two-stage by design: the image carries a working build so a fresh clone can
# `make up` with no host Node.
#
# NOTE: the build CONTEXT is ./frontend (sibling of this folder), not
# ./frontend/web, because the drag-and-drop grid lives in
# frontend/circuit_composer and is pulled in through the @composer alias (see
# vite.config.ts). It is source, not a built bundle, so this app compiles it.
#
#   docker build -f web/Dockerfile .     # from ./frontend
#
#   docker build -f web/Dockerfile .     # from ./frontend

FROM node:22-alpine AS build
WORKDIR /build

COPY web/package.json web/package-lock.json ./web/
RUN cd web && npm ci --no-audit --no-fund

COPY web ./web
  # The shared grid source; keep in step with the @composer alias in
  # vite.config.ts, which is what makes this path resolvable at build time.
COPY circuit_composer/frontend/src ./circuit_composer/frontend/src

RUN cd web && npm run build

FROM nginx:1.27-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/web/dist /usr/share/nginx/html
EXPOSE 80
