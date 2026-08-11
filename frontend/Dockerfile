FROM node:20-slim AS builder

WORKDIR /app

ENV NUXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-slim AS runner

ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000
ENV NUXT_BACKEND_BASE_URL=http://backend:8000

WORKDIR /app

COPY --from=builder /app/.output .output
COPY --from=builder /app/node_modules node_modules
COPY --from=builder /app/package.json package.json

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
