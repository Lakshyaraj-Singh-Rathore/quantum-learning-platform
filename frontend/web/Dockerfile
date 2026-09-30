# Two-stage by design, mirroring how the frozen Streamlit stack treats its
# composer bundle: the image carries a working build so a fresh clone can
# `make up` with no host Node, while `make web-build` on the host drops a
# fresh dist over the bind mount for iteration. Neither path needs anything
# installed on Windows — Node only ever runs inside a container.

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
