#!/bin/sh
# Emits window.__NEUROFLOW_CONFIG__ from container-start-time environment
# variables, so the same built image can point at any backend without a
# rebuild -- see docs/18-deployment-and-operations.md #18.2 and
# src/config/env.ts. Runs before nginx starts serving.
set -eu

API_BASE_URL="${API_BASE_URL:-/api/v1}"

cat > /usr/share/nginx/html/config.js <<JS
window.__NEUROFLOW_CONFIG__ = {
  apiBaseUrl: "${API_BASE_URL}"
};
JS

exec "$@"
