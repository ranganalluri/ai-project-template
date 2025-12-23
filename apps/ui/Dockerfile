# Multi-stage build for React UI

FROM node:18-alpine as builder

WORKDIR /build

RUN npm install -g pnpm

# Copy workspace files
COPY package.json pnpm-workspace.yaml ./
# Copy ui-lib and apps/ui
COPY apps/ui-lib apps/ui-lib
COPY apps/ui apps/ui

# Install dependencies using pnpm
RUN pnpm install

# Build ui-lib first
RUN pnpm --filter=./apps/ui-lib build

# Build the UI app
RUN pnpm --filter=./apps/ui build

# Runtime stage
FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve

# Copy built files
COPY --from=builder /build/apps/ui/dist ./dist

# Copy the env config generation script
COPY apps/ui/generate-env-config.sh ./generate-env-config.sh
RUN chmod +x ./generate-env-config.sh

EXPOSE 5173

# Generate runtime config and serve
CMD ["sh", "-c", "./generate-env-config.sh && serve -s dist -l 5173"]
