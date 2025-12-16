# Multi-stage build for React UI
FROM node:18-alpine as builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN npm ci

COPY apps/ui apps/ui

RUN npm run build --workspace=@agentic/ui

# Runtime stage
FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /build/apps/ui/dist ./dist

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget -q -O- http://localhost:3000 || exit 1

CMD ["serve", "-s", "dist", "-l", "3000"]
