#!/bin/bash

echo "=== FalconDeck Phase 4 Installer ==="

cd ~/FalconDeck_MkV || exit 1

cp map.py map.py.backup

python3 patch_phase4.py

if [ $? -ne 0 ]; then
    echo "Patch failed."
    cp map.py.backup map.py
    exit 1
fi

python3 -m py_compile map.py

if [ $? -ne 0 ]; then
    echo "Python compile failed."
    cp map.py.backup map.py
    exit 1
fi

echo
echo "Update installed successfully."
echo

sudo reboot
