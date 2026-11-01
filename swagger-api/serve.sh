#!/bin/bash
# Serve the Swagger page on port 8080 without Docker.
set -euo pipefail
cd "$(dirname "$0")"
exec python3 server.py
