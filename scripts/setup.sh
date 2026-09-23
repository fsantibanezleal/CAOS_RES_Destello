#!/usr/bin/env bash
# Create the two environments: .venv (tests, guards) and .venv-pipeline (the offline pipeline). Python 3.12.
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v python3.12 >/dev/null 2>&1; then PY=(python3.12); else PY=(py -3.12); fi
"${PY[@]}" -m venv .venv
"${PY[@]}" -m venv .venv-pipeline
BIN=bin
if [ -d .venv/Scripts ]; then BIN=Scripts; fi
.venv/$BIN/python -m pip install -q --upgrade pip
.venv/$BIN/python -m pip install -q -r requirements.txt -r requirements-dev.txt
.venv-pipeline/$BIN/python -m pip install -q --upgrade pip
.venv-pipeline/$BIN/python -m pip install -q -r requirements-precompute.txt -r requirements-dev.txt
echo "setup: .venv and .venv-pipeline ready"
