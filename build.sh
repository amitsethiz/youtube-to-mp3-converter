#!/usr/bin/env bash
set -e

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing Python dependencies (includes bundled FFmpeg via imageio-ffmpeg)..."
pip install -r requirements.txt

echo "==> Build complete!"
