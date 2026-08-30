#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
project_root=${script_dir:h}
app_path=${1:-}
app_version=$(/usr/bin/tr -d '[:space:]' < "$project_root/VERSION")
dmgbuild_bin=${DMGBUILD_BIN:-$project_root/.venv/bin/dmgbuild}
dmgbuild_python=${DMGBUILD_PYTHON:-${dmgbuild_bin:h}/python}
volume_name="Antarctic Atlas $app_version"
artifact_name="Antarctic-Atlas-v${app_version}-macOS-arm64.dmg"
artifact_dir="$project_root/dist"
dmg_path=${2:-$artifact_dir/$artifact_name}
checksum_path="$dmg_path.sha256"

if [[ $(uname -s) != Darwin || $(uname -m) != arm64 ]]; then
  print -u2 'DMG packaging currently targets Apple Silicon macOS.'
  exit 1
fi

if [[ -z "$app_path" || ! -d "$app_path" || "${app_path:e}" != app ]]; then
  print -u2 'Usage: scripts/build-dmg.sh /path/to/Antarctic Atlas.app [output.dmg]'
  exit 1
fi
app_path=${app_path:A}

if [[ ! -x "$dmgbuild_bin" || ! -x "$dmgbuild_python" ]]; then
  print -u2 'dmgbuild is missing. Run scripts/setup-macos.sh first.'
  exit 1
fi

app_plist="$app_path/Contents/Info.plist"
app_binary="$app_path/Contents/MacOS/Antarctic Atlas"
if [[ ! -f "$app_plist" || ! -x "$app_binary" ]]; then
  print -u2 "Incomplete application bundle: $app_path"
  exit 1
fi

bundle_version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app_plist")
if [[ "$bundle_version" != "$app_version" ]]; then
  print -u2 "Application version mismatch: expected $app_version, found $bundle_version"
  exit 1
fi

xcode_developer='/Applications/Xcode.app/Contents/Developer'
xcode_toolchain="$xcode_developer/Toolchains/XcodeDefault.xctoolchain/usr/bin"
xcode_setfile="$xcode_developer/usr/bin/SetFile"
xcode_getfileinfo="$xcode_developer/usr/bin/GetFileInfo"
if [[ ! -x "$xcode_toolchain/lipo" || ! -x "$xcode_setfile" || ! -x "$xcode_getfileinfo" ]]; then
  print -u2 'Xcode.app with lipo, SetFile, and GetFileInfo is required for DMG validation.'
  exit 1
fi
architectures=$("$xcode_toolchain/lipo" -archs "$app_binary")
if [[ "$architectures" != arm64 ]]; then
  print -u2 "Expected an arm64 app, found: $architectures"
  exit 1
fi
/usr/bin/codesign --verify --deep --strict "$app_path"

verify_root=$(mktemp -d /private/tmp/antarctic-atlas-dmg.XXXXXX)
case "$verify_root" in
  /private/tmp/antarctic-atlas-dmg.*) ;;
  *)
    print -u2 "Unexpected temporary path: $verify_root"
    exit 1
    ;;
esac
mount_path="$verify_root/mount"
background_path="$project_root/installer/dmg-background.png"
mounted=0

cleanup_dmg() {
  if (( mounted != 0 )); then
    /usr/bin/hdiutil detach "$mount_path" -quiet || true
  fi
  [[ -d "$verify_root" ]] && /bin/rm -rf -- "$verify_root"
}
trap cleanup_dmg EXIT

/bin/mkdir -p "${dmg_path:h}"
/bin/rm -f -- "$dmg_path" "$checksum_path"

background_width=$(/usr/bin/sips -g pixelWidth "$background_path" 2>/dev/null | \
  /usr/bin/awk '/pixelWidth:/ {print $2}')
background_height=$(/usr/bin/sips -g pixelHeight "$background_path" 2>/dev/null | \
  /usr/bin/awk '/pixelHeight:/ {print $2}')
if [[ "$background_width" != 680 || "$background_height" != 440 ]]; then
  print -u2 "Unexpected DMG background size: ${background_width}x${background_height}"
  exit 1
fi

ANTARCTIC_ATLAS_SETFILE="$xcode_setfile" \
"$dmgbuild_python" "$project_root/scripts/run-dmgbuild.py" \
  --settings "$project_root/installer/dmg_settings.py" \
  --app "$app_path" \
  --background "$background_path" \
  --volume-icon "$project_root/installer/antarctic_atlas.icns" \
  "$volume_name" \
  "$dmg_path"

/usr/bin/hdiutil verify "$dmg_path"
/bin/mkdir -p "$mount_path"
/usr/bin/hdiutil attach \
  -readonly \
  -nobrowse \
  -noverify \
  -mountpoint "$mount_path" \
  "$dmg_path" >/dev/null
mounted=1

mounted_app="$mount_path/Antarctic Atlas.app"
if [[ ! -d "$mounted_app" ]]; then
  print -u2 'DMG does not contain Antarctic Atlas.app.'
  exit 1
fi
if [[ ! -L "$mount_path/Applications" || $(/usr/bin/readlink "$mount_path/Applications") != /Applications ]]; then
  print -u2 'DMG does not contain the expected Applications shortcut.'
  exit 1
fi
if [[ ! -f "$mount_path/.DS_Store" || ! -f "$mount_path/.VolumeIcon.icns" ]]; then
  print -u2 'DMG is missing its Finder layout or volume icon.'
  exit 1
fi
finder_attributes=$("$xcode_getfileinfo" -a "$mount_path")
if [[ "$finder_attributes" != *C* ]]; then
  print -u2 'DMG volume is missing its custom-icon Finder flag.'
  exit 1
fi
visible_entries=$(/usr/bin/find "$mount_path" -mindepth 1 -maxdepth 1 ! -name '.*' \
  -exec /usr/bin/basename {} \; | /usr/bin/sort)
expected_entries=$'Antarctic Atlas.app\nApplications'
if [[ "$visible_entries" != "$expected_entries" ]]; then
  print -u2 'DMG root must expose only Antarctic Atlas.app and Applications.'
  print -u2 -- "$visible_entries"
  exit 1
fi

/usr/bin/codesign --verify --deep --strict "$mounted_app"
install_root="$verify_root/install"
installed_app="$install_root/Antarctic Atlas.app"
/bin/mkdir -p "$install_root"
/usr/bin/ditto "$mounted_app" "$installed_app"
/usr/bin/codesign --verify --deep --strict "$installed_app"
installed_version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
  "$installed_app/Contents/Info.plist")
if [[ "$installed_version" != "$app_version" ]]; then
  print -u2 "Installed application version mismatch: $installed_version"
  exit 1
fi
installed_architectures=$("$xcode_toolchain/lipo" -archs \
  "$installed_app/Contents/MacOS/Antarctic Atlas")
if [[ "$installed_architectures" != arm64 ]]; then
  print -u2 "Installed application architecture mismatch: $installed_architectures"
  exit 1
fi

smoke_root="$verify_root/smoke"
/bin/mkdir -p "$smoke_root"
QT_QPA_PLATFORM=offscreen \
QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu \
ANTARCTIC_ATLAS_CONFIG_DIR="$smoke_root/config" \
ANTARCTIC_ATLAS_CACHE_DIR="$smoke_root/cache" \
ANTARCTIC_ATLAS_SMOKE_TEST=1 \
  "$installed_app/Contents/MacOS/Antarctic Atlas"

/usr/bin/hdiutil detach "$mount_path" -quiet
mounted=0

(
  cd "${dmg_path:h}"
  /usr/bin/shasum -a 256 "${dmg_path:t}" > "${checksum_path:t}"
)
(
  cd "${dmg_path:h}"
  /usr/bin/shasum -a 256 -c "${checksum_path:t}"
)

print "Built and verified drag-to-install DMG: $dmg_path"
print "SHA-256: $checksum_path"
