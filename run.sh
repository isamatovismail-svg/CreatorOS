#!/usr/bin/env bash
# CreatorOS Single-Command Launcher
# Usage: ./run.sh

cd "$(dirname "$0")"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

python manage.py run_creatoros "$@"
