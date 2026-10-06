#!/usr/bin/env bash
# =============================================================================
# Create (or refresh) the project virtual environment .venv on Linux and verify it.
#
# Preferred path: uv + the committed universal lock file (uv.lock): exact,
# tested versions; Python version from .python-version (uv downloads it).
# Fallback without uv: python3 -m venv + pip with the ranges of pyproject.toml
# (works, but NOT locked).
#
# The .venv folder is machine specific: never copy it from Windows. If a
# Windows .venv is found (Scripts/ instead of bin/), it is recreated.
#
# Usage:
#   ./setup_linux.sh                       # core + aria + dev, then tests
#   ./setup_linux.sh --extras aria,cv      # add the experimental CV back-end (large torch download)
#   ./setup_linux.sh --egoblur             # also create .venv-egoblur (Meta EgoBlur, separate env)
#   ./setup_linux.sh --recreate --skip-tests
# Options:
#   --extras LIST   comma-separated extras (default: aria). Available: aria, cv, presentation
#   --no-dev        do not install pytest/ruff (tests skipped)
#   --recreate      delete .venv first
#   --skip-tests    do not run the test suite
#   --python PATH   interpreter for the pip fallback (default: python3.12/3.11/3.10)
#   --egoblur       create .venv-egoblur with egoblur==2.0.1 (incompatible with projectaria-tools
#                   in one environment: moviepy<2 vs >=2). Model weights must be downloaded
#                   manually after accepting their licence (docs/privacy_pipeline.md).
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

EXTRAS="aria"
DEV=1
RECREATE=0
TESTS=1
PYTHON=""
EGOBLUR=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --extras) EXTRAS="$2"; shift 2 ;;
    --no-dev) DEV=0; shift ;;
    --recreate) RECREATE=1; shift ;;
    --skip-tests) TESTS=0; shift ;;
    --python) PYTHON="$2"; shift 2 ;;
    --egoblur) EGOBLUR=1; shift ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

IFS=',' read -r -a EXTRA_LIST <<< "$EXTRAS"
if [[ $DEV -eq 1 ]]; then EXTRA_LIST+=("dev"); fi

find_uv() {
  if command -v uv >/dev/null 2>&1; then command -v uv; return 0; fi
  for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
    if [[ -x "$candidate" ]]; then echo "$candidate"; return 0; fi
  done
  return 1
}

# A .venv copied from Windows is never reused.
if [[ -d .venv && ! -x .venv/bin/python ]]; then
  echo "WARNING: .venv exists but is not a Linux environment (copied from Windows?). Recreating it."
  RECREATE=1
fi
if [[ $RECREATE -eq 1 && -d .venv ]]; then
  echo "Removing existing .venv"
  rm -rf .venv
fi

if UV="$(find_uv)"; then
  ARGS=(sync --frozen)
  for extra in "${EXTRA_LIST[@]}"; do
    if [[ -n "$extra" ]]; then ARGS+=(--extra "$extra"); fi
  done
  echo "Running: $UV ${ARGS[*]}"
  "$UV" "${ARGS[@]}"
else
  echo "WARNING: uv not found - falling back to venv + pip (versions NOT locked)."
  echo "         Install uv for reproducible environments: https://docs.astral.sh/uv/"
  if [[ ! -x .venv/bin/python ]]; then
    if [[ -z "$PYTHON" ]]; then
      for candidate in python3.12 python3.11 python3.10 python3; do
        if command -v "$candidate" >/dev/null 2>&1 && \
           "$candidate" -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)'; then
          PYTHON="$candidate"; break
        fi
      done
    fi
    if [[ -z "$PYTHON" ]]; then
      echo "ERROR: no Python 3.10-3.12 found (projectaria-tools supports 3.10-3.12). Install one or uv." >&2
      exit 1
    fi
    echo "Creating .venv with $PYTHON"
    if ! "$PYTHON" -m venv .venv; then
      echo "ERROR: venv creation failed. On Debian/Ubuntu install the venv module (python3-venv) or use uv." >&2
      exit 1
    fi
  fi
  .venv/bin/python -m pip install --upgrade pip
  SPEC="."
  JOINED="$(IFS=,; echo "${EXTRA_LIST[*]}")"
  if [[ -n "$JOINED" ]]; then SPEC=".[${JOINED}]"; fi
  .venv/bin/python -m pip install -e "$SPEC"
fi

echo
echo "=== Installation check ==="
.venv/bin/python -m ariagen_escooter info

if [[ $TESTS -eq 1 && $DEV -eq 1 ]]; then
  echo
  echo "=== Test suite ==="
  .venv/bin/python -m pytest -q
fi

if [[ $EGOBLUR -eq 1 ]]; then
  echo
  echo "=== Separate EgoBlur environment (.venv-egoblur) ==="
  if UV="$(find_uv)"; then
    "$UV" venv --python 3.11 .venv-egoblur
    "$UV" pip install --python .venv-egoblur/bin/python "egoblur==2.0.1"
  else
    "${PYTHON:-python3}" -m venv .venv-egoblur
    .venv-egoblur/bin/python -m pip install --upgrade pip "egoblur==2.0.1"
  fi
  .venv-egoblur/bin/egoblur-vrs-blur --help >/dev/null && echo "egoblur-vrs-blur available in .venv-egoblur/bin/"
  echo "Download the Gen 2 model weights manually (licence acceptance required): see docs/privacy_pipeline.md"
fi

echo
echo "Environment ready. Activate it with:  source .venv/bin/activate"
echo "Try the synthetic MVP:               python -m ariagen_escooter run data/synthetic/SYN001_S01"
