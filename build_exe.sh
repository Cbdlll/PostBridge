#!/bin/bash
# PostBridge - Linux/macOS build script

set -e

echo "========================================"
echo " PostBridge - Build"
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/4] Building frontend..."
cd postbridge_frontend
npm install
npm run build

echo "[2/4] Copying frontend files to backend..."
mkdir -p ../postbridge_backend/static
cp -r dist/* ../postbridge_backend/static/
cd ..

echo "[3/4] Installing Python dependencies..."
cd postbridge_backend
pip install -r requirements.txt -q
pip install pyinstaller -q

echo "[4/4] Building executable..."
pyinstaller --clean --noconfirm app.spec

echo ""
echo "========================================"
echo " Build complete!"
echo " Output: postbridge_backend/dist/PostBridge"
echo "========================================"
