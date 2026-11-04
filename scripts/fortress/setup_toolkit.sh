#!/usr/bin/env bash
# Set up the HDR RO-Crate Toolkits for submitting to the DemoStack:
# creates .venv, installs the toolkit and 5s-crate-py, and creates .env and
# 5s-tes-wb-config.yaml from templates if they don't exist.
#
# Usage: scripts/fortress/setup_toolkit.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 13))'; then
    echo "ERROR: Python 3.13+ is required (found $(python3 --version))." >&2
    exit 1
fi

[ -d .venv ] || { echo "==> Creating .venv"; python3 -m venv .venv; }

echo "==> Installing toolkit"
.venv/bin/pip install -q -e ".[dev]"
echo "==> Installing 5s-crate-py"
.venv/bin/pip install -q "git+https://github.com/eScienceLab/5s-crate-py"

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
