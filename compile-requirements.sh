#!/usr/bin/env bash
# Script to manage dependencies using pip-compile
# Usage: ./compile-requirements.sh [--upgrade]

set -e

echo "🔄 EIS Requirements Compiler"
echo "=========================================="

# Check if pip-compile is installed
if ! command -v pip-compile &> /dev/null; then
    echo "📦 Installing pip-tools..."
    pip install pip-tools
fi

# Handle upgrade flag
UPGRADE_FLAG=""
if [[ "$1" == "--upgrade" ]]; then
    UPGRADE_FLAG="--upgrade"
    echo "⬆️  Compiling with dependency upgrade..."
else
    echo "📝 Compiling requirements (preserving locked versions)..."
fi

# Compile base requirements
echo ""
echo "1️⃣  Compiling requirements.txt from requirements.in..."
pip-compile $UPGRADE_FLAG \
    requirements.in \
    --output-file=requirements.txt \
    --resolver=backtracking \
    --quiet

echo "   ✓ requirements.txt generated"

# Compile development requirements
echo ""
echo "2️⃣  Compiling requirements-dev.txt from requirements-dev.in..."
pip-compile $UPGRADE_FLAG \
    requirements-dev.in \
    --output-file=requirements-dev.txt \
    --resolver=backtracking \
    --quiet

echo "   ✓ requirements-dev.txt generated"

echo ""
echo "✅ Requirements compilation complete!"
echo ""
echo "📌 Next steps:"
echo "   - Development:  pip install -r requirements-dev.txt"
echo "   - Production:   pip install -r requirements.txt"
echo "   - Update deps:  ./compile-requirements.sh --upgrade"
