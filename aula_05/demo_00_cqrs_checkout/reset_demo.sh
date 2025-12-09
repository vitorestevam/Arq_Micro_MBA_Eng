#!/bin/bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -f "${BASE_DIR}/read_model.db"

echo "✅ Read model removido. Recrie com 'python projection.py'."
