#!/bin/bash
# Setup script for dolphin-expr environment
# This adds the dolphin SDK to PYTHONPATH

export PYTHONPATH="/Users/xupeng/dev/github/dolphin/src:$PYTHONPATH"
echo "✓ PYTHONPATH configured for dolphin SDK"
echo "  Dolphin source: ~/dev/github/dolphin/src"
echo ""
echo "You can now run:"
echo "  ./bin/run --name bird_baseline --status"
