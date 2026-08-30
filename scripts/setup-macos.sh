#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
project_root=${script_dir:h}

if [[ $(uname -s) != Darwin || $(uname -m) != arm64 ]]; then
  print -u2 'This setup script currently targets Apple Silicon macOS.'
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  print -u2 'uv is required. Install it first, then rerun this script.'
  exit 1
fi

cache_root=$(getconf DARWIN_USER_CACHE_DIR)
venv_target=${ANTARCTIC_ATLAS_DEV_VENV:-"${cache_root%/}/antarctic-atlas/dev-venv"}
venv_link="$project_root/.venv"

if [[ -e "$venv_link" && ! -L "$venv_link" ]]; then
  print -u2 "$venv_link is a real directory. Move it aside before running this setup."
  print -u2 'The macOS environment must live outside the project working tree.'
  exit 1
fi

/bin/mkdir -p "${venv_target:h}"

cd "$project_root"
uv venv --python 3.12 "$venv_target"

if [[ -L "$venv_link" && "$(readlink "$venv_link")" != "$venv_target" ]]; then
  print -u2 "$venv_link points to an unexpected environment; refusing to replace it."
  exit 1
fi
if [[ ! -L "$venv_link" ]]; then
  ln -s "$venv_target" "$venv_link"
fi

uv pip install --python "$venv_target/bin/python" \
  -r requirements-desktop.txt \
  -r requirements-dev.txt

print 'macOS desktop environment is ready.'
print "Environment: $venv_target"
print 'Run: .venv/bin/python scripts/macos-smoke.py'
