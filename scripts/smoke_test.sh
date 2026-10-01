#!/usr/bin/env bash
# Smoke test script for local or CI validation
# Usage: ./scripts/smoke_test.sh [URL]

set -euo pipefail

URL="${1:-http://localhost:8080}"
echo "Running smoke tests against $URL..."

echo "1. Checking readiness endpoint..."
for i in $(seq 1 10); do
  if curl -fsS "$URL/health/ready" >/dev/null; then
    echo "✓ Readiness probe passed"
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "✗ Readiness probe failed"
    exit 1
  fi
  sleep 2
done

echo "2. Checking health payload..."
HEALTH_STATUS=$(curl -fsS "$URL/health" | grep -q '"status":"healthy"' && echo "pass" || echo "fail")
if [ "$HEALTH_STATUS" = "pass" ]; then
  echo "✓ Health payload is valid"
else
  echo "✗ Health payload invalid"
  exit 1
fi

echo "3. Checking UI language default..."
HTML_LANG=$(curl -fsS "$URL/" | grep -q 'lang="hi"' && echo "pass" || echo "fail")
if [ "$HTML_LANG" = "pass" ]; then
  echo "✓ HTML language is Hindi"
else
  echo "✗ HTML language is not Hindi"
  exit 1
fi

echo "4. Checking security headers..."
HEADERS=$(curl -sI "$URL/health")
if echo "$HEADERS" | grep -qi "x-content-type-options"; then
  echo "✓ X-Content-Type-Options is present"
else
  echo "✗ X-Content-Type-Options is missing"
  exit 1
fi

if echo "$HEADERS" | grep -qi "x-frame-options"; then
  echo "✓ X-Frame-Options is present"
else
  echo "✗ X-Frame-Options is missing"
  exit 1
fi

echo "All smoke tests passed successfully! ✨"
