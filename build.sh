#!/bin/bash
set -e
echo "Python version: $(python3 --version)"
echo "Pip version: $(pip --version)"
pip install --upgrade pip
pip install -r requirements.txt 2>&1
echo "Build complete!"
