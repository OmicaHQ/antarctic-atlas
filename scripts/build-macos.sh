#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
project_root=${script_dir:h}
python_bin="$project_root/.venv/bin/python"
uv_bin=$(command -v uv || true)
app_version=$(/usr/bin/tr -d '[:space:]' < "$project_root/VERSION")
version_pattern='^[0-9]+\.[0-9]+\.[0-9]+$'

if [[ ! "$app_version" =~ $version_pattern ]]; then
  print -u2 "Invalid VERSION value: $app_version"
  exit 1
fi

if [[ $(uname -s) != Darwin || $(uname -m) != arm64 ]]; then
  print -u2 'This build script currently targets Apple Silicon macOS.'
  exit 1
fi

if [[ ! -x "$python_bin" ]]; then
  print -u2 'Missing .venv. Run scripts/setup-macos.sh first.'
  exit 1
fi

if [[ -z "$uv_bin" || ! -x "$uv_bin" ]]; then
  print -u2 'uv is required. Run scripts/setup-macos.sh first.'
  exit 1
fi

# Prefer the real Xcode toolchain over the Command Line Tools license shim.
# PyInstaller needs `lipo` to thin its universal bootloader to arm64.
xcode_toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin'
if [[ -x "$xcode_toolchain/lipo" ]]; then
  export PATH="$xcode_toolchain:$PATH"
else
  print -u2 'Xcode.app with its arm64 lipo tool is required for packaging.'
  exit 1
fi

build_root=$(mktemp -d /private/tmp/antarctic-atlas-build.XXXXXX)
case "$build_root" in
  /private/tmp/antarctic-atlas-build.*) ;;
  *)
    print -u2 "Unexpected temporary build path: $build_root"
    exit 1
    ;;
esac

cleanup_build_root() {
  [[ -d "$build_root" ]] && /bin/rm -rf -- "$build_root"
}
trap cleanup_build_root EXIT

cd "$project_root"
print 'Preparing an isolated packaging environment...'
"$uv_bin" venv --python "$python_bin" "$build_root/venv"
UV_LINK_MODE=copy "$uv_bin" pip install \
  --python "$build_root/venv/bin/python" \
  -r requirements-desktop.txt \
  -r requirements-dev.txt

build_python="$build_root/venv/bin/python"
"$build_python" -m PyInstaller \
  --noconfirm \
  --clean \
  --distpath "$build_root/dist" \
  --workpath "$build_root/build" \
  'Antarctic Atlas macOS.spec'

app_path="$build_root/dist/Antarctic Atlas.app"
if [[ ! -d "$app_path" ]]; then
  print -u2 "Build did not create $app_path"
  exit 1
fi

# Sign in a private temporary directory and publish a zip archive, which
# preserves the verified bundle until it is extracted for installation.
/usr/bin/xattr -cr "$app_path"
/usr/bin/codesign --force --deep --sign - "$app_path"
/usr/bin/codesign --verify --deep --strict "$app_path"

binary_path="$app_path/Contents/MacOS/Antarctic Atlas"
architectures=$("$xcode_toolchain/lipo" -archs "$binary_path")
if [[ "$architectures" != arm64 ]]; then
  print -u2 "Expected an arm64 app, found: $architectures"
  exit 1
fi

artifact_dir="$project_root/dist"
artifact_name="Antarctic-Atlas-v${app_version}-macOS-arm64.zip"
artifact_path="$artifact_dir/$artifact_name"
checksum_path="$artifact_path.sha256"
/bin/mkdir -p "$artifact_dir"
/bin/rm -f -- "$artifact_path"
/bin/rm -f -- "$checksum_path"
/usr/bin/ditto -c -k --norsrc --noextattr --noqtn --keepParent "$app_path" "$artifact_path"

verify_dir="$build_root/verify"
/bin/mkdir -p "$verify_dir"
/usr/bin/ditto -x -k "$artifact_path" "$verify_dir"
verified_app="$verify_dir/Antarctic Atlas.app"
/usr/bin/codesign --verify --deep --strict "$verified_app"

smoke_root="$build_root/smoke"
/bin/mkdir -p "$smoke_root"
QT_QPA_PLATFORM=offscreen \
QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
ANTARCTIC_ATLAS_CONFIG_DIR="$smoke_root/config" \
ANTARCTIC_ATLAS_CACHE_DIR="$smoke_root/cache" \
ANTARCTIC_ATLAS_SMOKE_TEST=1 \
  "$verified_app/Contents/MacOS/Antarctic Atlas"

# macOS 27 currently caches the packaged, thinned Qt plug-ins in a way that can
# temporarily shadow the universal plug-ins in the development environment.
# Reinstalling these four already-cached wheels refreshes their file identities
# without a network request and leaves source development usable after a build.
pyside_version=$(/usr/bin/sed -n 's/^PySide6==//p' requirements-desktop.txt)
if [[ -z "$pyside_version" ]]; then
  print -u2 'Could not determine the pinned PySide6 version.'
  exit 1
fi
print 'Refreshing the local Qt development runtime...'
UV_LINK_MODE=copy "$uv_bin" pip install \
  --offline \
  --python "$python_bin" \
  --reinstall \
  "pyside6==$pyside_version" \
  "pyside6-addons==$pyside_version" \
  "pyside6-essentials==$pyside_version" \
  "shiboken6==$pyside_version"

QT_QPA_PLATFORM=offscreen "$python_bin" - <<'PY'
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

app = QApplication([])
QTimer.singleShot(0, app.quit)
app.exec()
print("MACOS_DEV_QT_OK")
PY

(
  cd "$artifact_dir"
  /usr/bin/shasum -a 256 "$artifact_name" > "${artifact_name}.sha256"
)

print "Built and verified: $artifact_path"
print "SHA-256: $checksum_path"
print 'The app has an ad-hoc development signature. Developer ID signing and notarization are separate release steps.'
