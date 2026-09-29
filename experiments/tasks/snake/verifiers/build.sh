#!/bin/sh
set -eu
TASK_DIR=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
WORKSPACE=${SCC_WORKSPACE:-$(pwd)}
if [ ! -d "$WORKSPACE/demos/snake" ]; then
  printf '%s\n' 'ERROR: SCC_WORKSPACE does not contain demos/snake' >&2
  exit 2
fi
exec python3 "$TASK_DIR/verifiers/verify.py" build
