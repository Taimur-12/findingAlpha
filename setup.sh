#!/usr/bin/env bash
# Sets up the finding_alpha development environment on macOS/Linux.
# Run once after cloning: bash setup.sh

set -e

PYTHON_MIN="3.12"
VENV_DIR=".venv"

# ── Check Python version ───────────────────────────────────────────────────────
check_python() {
    local py="$1"
    if ! command -v "$py" &>/dev/null; then return 1; fi
    "$py" -c "
import sys
req = tuple(int(x) for x in '${PYTHON_MIN}'.split('.'))
sys.exit(0 if sys.version_info[:2] >= req else 1)
" 2>/dev/null
}

PYTHON=""
for candidate in python3.12 python3 python; do
    if check_python "$candidate"; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "ERROR: Python $PYTHON_MIN+ not found."
    echo ""
    echo "Install it with one of:"
    echo "  brew install python@3.12          # Homebrew"
    echo "  conda create -n finding_alpha python=3.12 && conda activate finding_alpha"
    echo "  pyenv install 3.12 && pyenv local 3.12"
    echo ""
    exit 1
fi

echo "Using Python: $($PYTHON --version)"

# ── Create virtual environment ─────────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR — skipping creation."
else
    echo "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

# ── Install dependencies ───────────────────────────────────────────────────────
echo "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -e ".[dev,research]" --quiet

echo ""
echo "Installation complete. Verifying with a quick import check..."
python -c "
import finding_alpha
import pandas, numpy, pydantic, pyarrow
print('  Core imports OK')
"

# ── Run tests ─────────────────────────────────────────────────────────────────
echo ""
echo "Running test suite..."
pytest tests/ -v --tb=short

echo ""
echo "================================================================"
echo "Setup complete."
echo ""
echo "To activate the environment in future sessions:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest tests/ -v"
echo "================================================================"
