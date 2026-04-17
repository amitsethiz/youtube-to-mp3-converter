#!/usr/bin/env bash
set -e

echo "==> Installing system dependencies..."
apt-get update -y
apt-get install -y ffmpeg

echo "==> FFmpeg version:"
ffmpeg -version | head -1

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Build complete!"
