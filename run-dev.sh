#!/bin/bash
set -e

cd "$(dirname "$0")"

# First-time setup: Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv --system-site-packages venv
  echo "✓ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

# First-time setup: Install Python dependencies if not already installed
if ! python -c "import yt_dlp" 2>/dev/null; then
  echo "Installing Python dependencies..."
  pip install --upgrade pip
  pip install meson ninja pyxattr mutagen pycryptodomex websockets brotli yt-dlp-ejs yt-dlp[default]
  echo "✓ Dependencies installed"
fi

# First-time setup: Configure meson build directory if it doesn't exist
if [ ! -d "_build" ]; then
  echo "Configuring build directory..."
  meson setup _build --prefix="$PWD/install"
  echo "✓ Build directory configured"
fi

# Build the project
echo "Building project..."
meson compile -C _build

# Install to local directory
echo "Installing to local directory..."
meson install -C _build

# Run the application with proper environment
echo "Starting Video Downloader..."
GSETTINGS_SCHEMA_DIR=$PWD/install/share/glib-2.0/schemas \
  ./install/bin/video-downloader "$@"
