#!/bin/bash
# Setup script for dolphin-expr environment
# This adds the dolphin SDK to PYTHONPATH

if [ -z "${DOLPHIN_SRC}" ] && [ -n "${DOLPHIN_REPO}" ]; then
  export DOLPHIN_SRC="${DOLPHIN_REPO}/src"
fi

if [ -z "${DOLPHIN_SRC}" ]; then
  echo "✗ 未设置 dolphin 源码路径"
  echo "  请先设置：export DOLPHIN_SRC=/path/to/dolphin/src"
  echo "  或者设置：export DOLPHIN_REPO=/path/to/dolphin（会自动使用 /src）"
  echo ""
  echo "建议用法：source ./setup_env.sh"
  exit 1
fi

export PYTHONPATH="${DOLPHIN_SRC}:${PYTHONPATH:-}"
echo "✓ PYTHONPATH configured for dolphin SDK"
echo "  Dolphin source: ${DOLPHIN_SRC}"
echo ""
echo "You can now run:"
echo "  ./bin/run --name bird_baseline --status"
