#!/bin/bash
# Create a virtual key that can call Kiki and every loaded LFM checkpoint.
# Usage: ./create-key.sh alice
set -euo pipefail
cd "$(dirname "$0")"
name="${1:-}"
if [[ -z "${name}" || ! "${name}" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Usage: $0 <key-name>" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
curl -sS http://127.0.0.1:4000/key/generate \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"key_alias\":\"${name}\",\"models\":[\"kiki-tafsiri\",\"lfm3\",\"lfm3-1.7b-base\",\"lfm3-1.7b-fp8\",\"lfm3-vl-2b\",\"lfm3-audio-2b\",\"lfm3-omni-2b\"],\"rpm_limit\":60,\"tpm_limit\":100000}"
echo
