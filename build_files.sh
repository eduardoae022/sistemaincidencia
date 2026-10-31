#!/bin/bash
echo "Setting up Python 3.10 and building project packages..."
if command -v uv &> /dev/null; then
    uv python install 3.10
    uv pip install --system --python 3.10 -r requirements.txt
    uv run --python 3.10 python manage.py collectstatic --noinput --clear
else
    python3 -m pip install --break-system-packages -r requirements.txt
    python3 manage.py collectstatic --noinput --clear
fi
