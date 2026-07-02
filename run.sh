#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Launcher for auto_ut (Linux/macOS/WSL). POSIX-ish bash. Mirrors run.bat:
# runs from this script's dir, passes args through, prints a summary, and
# (if run in a terminal) waits for a keypress so you can read the result.
#   ./run.sh
#   ./run.sh --ask
#   ./run.sh --skip-flash
# ---------------------------------------------------------------------------
set -u
cd "$(dirname "$(readlink -f "$0")")" || exit 1

# prefer python3, fall back to python
PY="$(command -v python3 || command -v python)"
if [ -z "$PY" ]; then
  echo "error: python3 (or python) not found on PATH" >&2
  exit 127
fi

"$PY" autotest.py "$@"
RC=$?

echo
echo "============================================================"
echo " autotest finished, exit code = $RC   ( 0 = all PASS )"
echo " results : _ut_work/results/result.json"
echo " full log: _ut_work/logs/"
echo "============================================================"

# keep the window open only when interactive (won't hang in CI/pipes)
if [ -t 0 ]; then
  read -r -p "Press Enter to close..." _
fi
exit "$RC"
