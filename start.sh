#!/bin/bash
set -e

echo "============================================"
echo "=== Quran Reels Generator - Starting ==="
echo "============================================"

echo "[INFO] Current directory: $(pwd)"
echo "[INFO] Python version: $(python --version)"
echo "[INFO] Port: ${PORT:-7860}"
echo "[INFO] SPACE_ID: ${SPACE_ID:-not set}"
echo "[INFO] HF Space detected: ${SPACE_ID:+yes}${SPACE_ID:-no}"

# Use PORT env var if set (HuggingFace might override)
PORT="${PORT:-7860}"

echo "[INFO] Starting gunicorn on 0.0.0.0:${PORT}..."
exec gunicorn \
    -w 1 \
    --threads 4 \
    -b "0.0.0.0:${PORT}" \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    main:app
