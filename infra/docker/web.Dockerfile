FROM node:24-bookworm-slim

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
COPY frontend/quezo/package.json ./frontend/quezo/package.json
RUN --mount=type=secret,id=npm_ca \
    if [ -f /run/secrets/npm_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/npm_ca; fi; \
    npm ci
COPY tsconfig.base.json ./
COPY frontend/quezo ./frontend/quezo
COPY postgres/openapi.json ./postgres/openapi.json
RUN --mount=type=secret,id=npm_ca \
    if [ -f /run/secrets/npm_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/npm_ca; fi; \
    npm run build && npm prune --omit=dev

ENV NODE_ENV=production
USER node
EXPOSE 3000
CMD ["npm", "run", "start", "--workspace", "@quezo/web", "--", "--hostname", "0.0.0.0", "--port", "3000"]
