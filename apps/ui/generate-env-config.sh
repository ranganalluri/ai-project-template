#!/bin/sh
# Generate runtime environment configuration from environment variables

cat > /app/dist/env-config.js <<EOF
// Auto-generated runtime configuration
window.ENV = {
  VITE_API_URL: "${VITE_API_URL:-http://localhost:8000}",
  VITE_ENVIRONMENT: "${VITE_ENVIRONMENT:-production}"
}
EOF

echo "Generated env-config.js with:"
cat /app/dist/env-config.js
