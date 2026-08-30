#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
project_root=${script_dir:h}
python_bin="$project_root/.venv/bin/python"
uv_bin=$(command -v uv || true)
app_version=$(/usr/bin/tr -d '[:space:]' < "$project_root/VERSION")
version_pattern='^[0-9]+\.[0-9]+\.[0-9]+$'
minimum_macos_version='15.0'
codesign_identity=${ANTARCTIC_ATLAS_CODESIGN_IDENTITY:-}
entitlements_file=${ANTARCTIC_ATLAS_ENTITLEMENTS_FILE:-}

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
# PyInstaller needs `lipo` to thin its universal bootloader to arm64, and the
# release checks use `vtool` to verify every packaged Mach-O deployment target.
xcode_toolchain='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin'
if [[ -x "$xcode_toolchain/lipo" && -x "$xcode_toolchain/vtool" ]]; then
  export PATH="$xcode_toolchain:$PATH"
else
  print -u2 'Xcode.app with its lipo and vtool utilities is required for packaging.'
  exit 1
fi

if [[ -n "$entitlements_file" ]]; then
  if [[ "$entitlements_file" != /* ]]; then
    entitlements_file="$project_root/$entitlements_file"
  fi
  if [[ ! -f "$entitlements_file" ]]; then
    print -u2 "Entitlements file does not exist: $entitlements_file"
    exit 1
  fi
fi

if [[ -n "$codesign_identity" ]]; then
  identity_listing=$(/usr/bin/security find-identity -v -p codesigning 2>/dev/null || true)
  if ! print -r -- "$identity_listing" | /usr/bin/grep -F -- "$codesign_identity" >/dev/null; then
    print -u2 "Requested code-signing identity is not available: $codesign_identity"
    exit 1
  fi
  if ! print -r -- "$identity_listing" | /usr/bin/grep -F -- "$codesign_identity" | \
      /usr/bin/grep -F 'Developer ID Application:' >/dev/null; then
    print -u2 'Formal macOS builds require a Developer ID Application identity.'
    exit 1
  fi
  export ANTARCTIC_ATLAS_CODESIGN_IDENTITY="$codesign_identity"
  print 'Developer ID signing enabled.'
else
  print 'No Developer ID identity configured; building with an ad-hoc signature.'
fi

if [[ -n "$entitlements_file" ]]; then
  export ANTARCTIC_ATLAS_ENTITLEMENTS_FILE="$entitlements_file"
fi

version_exceeds() {
  local candidate=$1
  local limit=$2
  local candidate_major candidate_minor candidate_patch
  local limit_major limit_minor limit_patch

  IFS=. read -r candidate_major candidate_minor candidate_patch <<< "$candidate"
  IFS=. read -r limit_major limit_minor limit_patch <<< "$limit"
  candidate_minor=${candidate_minor:-0}
  candidate_patch=${candidate_patch:-0}
  limit_minor=${limit_minor:-0}
  limit_patch=${limit_patch:-0}

  (( candidate_major > limit_major )) || \
    (( candidate_major == limit_major && candidate_minor > limit_minor )) || \
    (( candidate_major == limit_major && candidate_minor == limit_minor && candidate_patch > limit_patch ))
}

verify_macos_compatibility() {
  local bundle_path=$1
  local bundle_minimum candidate build_info minos
  local candidate_minos_count
  local macho_count=0
  local highest_minos='0.0'
  local incompatible=0

  bundle_minimum=$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' \
    "$bundle_path/Contents/Info.plist")
  if [[ "$bundle_minimum" != "$minimum_macos_version" ]]; then
    print -u2 "Expected LSMinimumSystemVersion $minimum_macos_version, found $bundle_minimum"
    return 1
  fi

  while IFS= read -r -d '' candidate; do
    build_info=$("$xcode_toolchain/vtool" -show-build "$candidate" 2>/dev/null) || continue
    (( macho_count += 1 ))
    candidate_minos_count=0
    while IFS= read -r minos; do
      [[ -n "$minos" ]] || continue
      (( candidate_minos_count += 1 ))
      if version_exceeds "$minos" "$highest_minos"; then
        highest_minos=$minos
      fi
      if version_exceeds "$minos" "$minimum_macos_version"; then
        print -u2 "Mach-O requires macOS $minos (limit $minimum_macos_version): ${candidate#$bundle_path/}"
        incompatible=1
      fi
    done < <(print -r -- "$build_info" | /usr/bin/sed -n \
      's/^[[:space:]]*minos[[:space:]]*//p')
    if (( candidate_minos_count == 0 )); then
      print -u2 "Mach-O has no readable LC_BUILD_VERSION minimum: ${candidate#$bundle_path/}"
      incompatible=1
    fi
  done < <(/usr/bin/find "$bundle_path" -type f \
    \( -perm -111 -o -name '*.so' -o -name '*.dylib' \) -print0)

  if (( macho_count == 0 )); then
    print -u2 'No Mach-O files were found in the application bundle.'
    return 1
  fi
  if (( incompatible != 0 )); then
    return 1
  fi
  print "Mach-O deployment targets verified: files=$macho_count highest=$highest_minos minimum-macOS=$minimum_macos_version"
}

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
"$uv_bin" pip check --python "$build_python"
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

for bundled_resource in VERSION LICENSE THIRD_PARTY_NOTICES.md; do
  if [[ ! -f "$app_path/Contents/Resources/$bundled_resource" ]]; then
    print -u2 "Required release resource is missing: $bundled_resource"
    exit 1
  fi
done
packaged_version=$(/usr/bin/tr -d '[:space:]' < "$app_path/Contents/Resources/VERSION")
if [[ "$packaged_version" != "$app_version" ]]; then
  print -u2 "Packaged VERSION mismatch: expected $app_version, found $packaged_version"
  exit 1
fi

# Sign in a private temporary directory and publish a zip archive, which
# preserves the verified bundle until it is extracted for installation.
/usr/bin/xattr -cr "$app_path"
if [[ -z "$codesign_identity" ]]; then
  /usr/bin/codesign --force --deep --sign - "$app_path"
else
  signature_details=$(/usr/bin/codesign --display --verbose=4 "$app_path" 2>&1)
  if ! print -r -- "$signature_details" | /usr/bin/grep -F \
      'Authority=Developer ID Application:' >/dev/null; then
    print -u2 'PyInstaller did not preserve the requested Developer ID signature.'
    exit 1
  fi
  if ! print -r -- "$signature_details" | /usr/bin/grep -E \
      'flags=.*\(runtime\)' >/dev/null; then
    print -u2 'The Developer ID signature does not enable Hardened Runtime.'
    exit 1
  fi
fi
/usr/bin/codesign --verify --deep --strict "$app_path"
verify_macos_compatibility "$app_path"

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
dmg_name="Antarctic-Atlas-v${app_version}-macOS-arm64.dmg"
dmg_path="$artifact_dir/$dmg_name"
/bin/mkdir -p "$artifact_dir"
/bin/rm -f -- "$artifact_path"
/bin/rm -f -- "$checksum_path"
/bin/rm -f -- "$dmg_path"
/bin/rm -f -- "$dmg_path.sha256"
/usr/bin/ditto -c -k --norsrc --noextattr --noqtn --keepParent "$app_path" "$artifact_path"

verify_dir="$build_root/verify"
/bin/mkdir -p "$verify_dir"
/usr/bin/ditto -x -k "$artifact_path" "$verify_dir"
verified_app="$verify_dir/Antarctic Atlas.app"
/usr/bin/codesign --verify --deep --strict "$verified_app"
verify_macos_compatibility "$verified_app"

smoke_root="$build_root/smoke"
/bin/mkdir -p "$smoke_root"
QT_QPA_PLATFORM=offscreen \
QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
ANTARCTIC_ATLAS_CONFIG_DIR="$smoke_root/config" \
ANTARCTIC_ATLAS_CACHE_DIR="$smoke_root/cache" \
ANTARCTIC_ATLAS_SMOKE_TEST=1 \
  "$verified_app/Contents/MacOS/Antarctic Atlas"

DMGBUILD_BIN="$build_root/venv/bin/dmgbuild" \
DMGBUILD_PYTHON="$build_root/venv/bin/python" \
  "$script_dir/build-dmg.sh" "$verified_app" "$dmg_path"

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
print "Built and verified: $dmg_path"
print "SHA-256: $dmg_path.sha256"
if [[ -n "$codesign_identity" ]]; then
  print 'The app has a Developer ID signature with Hardened Runtime. Notarization and stapling remain separate release steps.'
else
  print 'The app has an ad-hoc development signature. Developer ID signing and notarization are separate release steps.'
fi
