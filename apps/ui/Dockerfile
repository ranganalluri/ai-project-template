# Multi-stage build for React UI


FROM node:18-alpine as builder

# Accept VITE_API_URL as build arg
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm install -g pnpm

WORKDIR /build

# Copy workspace files
COPY package.json pnpm-workspace.yaml ./
# Copy ui-lib and apps/ui
COPY apps/ui-lib apps/ui-lib
COPY apps/ui apps/ui

# Install dependencies using pnpm
RUN pnpm install

RUN pnpm  --filter=./apps/ui-lib build
# Build the UI app (adjust workspace name if needed)
RUN pnpm  --filter=./apps/ui build

# Runtime stage
FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /build/apps/ui/dist ./dist

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget -q -O- http://localhost:5173 || exit 1

CMD ["serve", "-s", "dist", "-l", "5173"]
