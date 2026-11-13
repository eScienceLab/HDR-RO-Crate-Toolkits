#!/usr/bin/env bash
# Set up the HDR RO-Crate Toolkits for submitting to the DemoStack:
# creates .venv, installs the toolkit, and creates .env and
# 5s-tes-wb-config.yaml from templates if they don't exist.
#
# Usage: scripts/fortress/setup_toolkit.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# Use the first Python 3.13+ found, so a newer python3.x works even if python3 is older.
PYTHON=""
for p in python3 python3.15 python3.14 python3.13; do
    if command -v "$p" >/dev/null && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 13))' 2>/dev/null; then
        PYTHON="$p"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3.13+ is required (python3 is $(python3 --version 2>&1))." >&2
    exit 1
fi

if [ -d .venv ] && ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 13))' 2>/dev/null; then
    echo "==> Existing .venv uses an older or broken Python, recreating it"
    rm -rf .venv
fi
[ -d .venv ] || { echo "==> Creating .venv with $("$PYTHON" --version)"; "$PYTHON" -m venv .venv; }

echo "==> Installing toolkit"
.venv/bin/pip install -q --disable-pip-version-check -e ".[dev]"

if [ ! -f .env ]; then
    cp env.template .env && echo "==> Created .env"
fi
if [ ! -f 5s-tes-wb-config.yaml ]; then
    cp scripts/fortress/5s-tes-wb-config.example.yaml 5s-tes-wb-config.yaml
    echo "==> Created 5s-tes-wb-config.yaml"
fi

cat <<MSG

Setup complete. Next:
  1. Fill in client_secret in 5s-tes-wb-config.yaml (see docs/fortress.md, step 6).
  2. From $REPO_ROOT, submit:
     .venv/bin/rocrate-tes-submit tests/data/fortress-5s-tes-pre-submission \\
         --config_path 5s-tes-wb-config.yaml --disable_roc_validator
  3. After egress is approved, fetch the results:
     .venv/bin/rocrate-tes-fetch tes-submission-ro-crate --config_path 5s-tes-wb-config.yaml
MSG
