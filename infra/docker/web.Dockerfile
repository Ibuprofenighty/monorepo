# Web image: builds the selected web client (blueprint 09 §5).
# Build from repo root:
#   Vite or Next static export:
#     docker build -f infra/docker/web.Dockerfile \
#       --build-arg APP=web --build-arg WEB_OUTPUT=dist \
#       --target runtime-static .
#   Next.js SSR (needs next.config.ts output: "standalone"):
#     docker build -f infra/docker/web.Dockerfile \
#       --build-arg APP=web-next --build-arg WEB_OUTPUT=server \
#       --target runtime-server .
#
# WEB_OUTPUT: dist (Vite) | out (Next static export) | server (Next SSR).
# The generator sets the default below from the answers file (web_rendering).
# Base images are digest-pinned. Node version and index digest: ADR 0007.
ARG APP=web
ARG WEB_OUTPUT=dist
ARG NODE_VERSION=24.11.1
ARG NODE_DIGEST=sha256:48abc13a19400ca3985071e287bd405a1d99306770eb81d61202fb6b65cf0b57
ARG NGINX_DIGEST=sha256:62223d644fa234c3a1cc785ee14242ec47a77364226f1c811d2f669f96dc2ac8

FROM node:${NODE_VERSION}-bookworm-slim@${NODE_DIGEST} AS builder
WORKDIR /app
ARG APP
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/ts/api-client/package.json packages/ts/api-client/
COPY apps/${APP}/package.json apps/${APP}/
RUN corepack enable && pnpm install --frozen-lockfile
COPY packages/ts/api-client packages/ts/api-client
COPY tooling tooling
COPY contracts contracts
COPY apps/${APP} apps/${APP}
# public/ is optional in an app; runtime-server copies it unconditionally.
RUN mkdir -p apps/${APP}/public && pnpm --filter ./apps/${APP} build

# --- static: nginx serves the build output (Vite dist / Next out) ---
FROM nginx:1.27-alpine@${NGINX_DIGEST} AS runtime-static
ARG APP
ARG WEB_OUTPUT
# The base digest stays pinned. Security updates that already have a fix are
# applied here so the image scan can fail when a newer fix appears.
RUN apk upgrade --no-cache
COPY infra/nginx/snippets/ /etc/nginx/snippets/
COPY infra/nginx/conf.d/app.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/${APP}/${WEB_OUTPUT} /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://127.0.0.1/ > /dev/null

# --- server: node runs Next.js standalone (SSR) ---
FROM node:${NODE_VERSION}-bookworm-slim@${NODE_DIGEST} AS runtime-server
WORKDIR /app
ARG APP
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
ENV NODE_ENV=production
ENV APP_DIR=apps/${APP}
COPY --from=builder /app/apps/${APP}/.next/standalone ./
COPY --from=builder /app/apps/${APP}/.next/static ./apps/${APP}/.next/static
COPY --from=builder /app/apps/${APP}/public ./apps/${APP}/public
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["sh", "-c", "node $APP_DIR/server.js"]
