#!/bin/bash

set -e

BASE="$HOME/FalconDeck_MkV"
UPDATE="$BASE/updates"
BACKUP="$BASE/backup"

echo "== FalconDeck Updater =="

mkdir -p "$BACKUP"

echo "Backing up current files..."
cp -a "$BASE"/*.py "$BACKUP"/ 2>/dev/null || true

echo "Installing updates..."
cp -f "$UPDATE"/*.py "$BASE"/ 2>/dev/null || true

echo "Checking Python files..."
python3 -m compileall "$BASE"

echo
echo "Update complete."
echo "Restarting FalconDeck..."
sudo reboot
