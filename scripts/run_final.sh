#!/usr/bin/env bash
# One final builder run with its own terminal log. Usage:
#   scripts/run_final.sh <case_folder> <mock_url> [extra build.py options, e.g. --contract FILE]
# - pipefail: the exit status is the builder's, not tee's
# - the terminal log name carries the time, so a second run never overwrites the first
# - the builder writes its own trace (traces/<slot>-<time>.log) and candidate folder (candidates/<slot>/<time>/);
#   the terminal log records which ones belong to this run (START / RESULT / END lines)
set -euo pipefail
case_folder="$1"; mock_url="$2"; shift 2
stamp="$(date -u +%Y%m%d-%H%M%S)"
slot="$(basename "${case_folder%/}")"
mkdir -p traces
log="traces/final-${slot}-${stamp}.terminal.log"
echo "commit $(git rev-parse HEAD) (builder tree $(git rev-parse HEAD:builder)), dirty files: $(git status --porcelain | wc -l)" | tee "$log"
python3 builder/build.py "$case_folder" "$mock_url" --slot "final-${slot}" "$@" 2>&1 | tee -a "$log"
echo "terminal log: $log"
