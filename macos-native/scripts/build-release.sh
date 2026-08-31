#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
NATIVE_DIR="${SCRIPT_DIR:h}"
REPO_DIR="${NATIVE_DIR:h}"
DIST_DIR="${REPO_DIR}/dist-native"
RELEASE_DIR="${REPO_DIR}/dist-native-release"
APP_NAME="Antarctic Atlas Native Preview"
APP_BUNDLE="${DIST_DIR}/${APP_NAME}.app"
VERSION="$(/usr/bin/tr -d '[:space:]' < "${REPO_DIR}/VERSION")"
VERSION_PATTERN='^[0-9]+\.[0-9]+\.[0-9]+$'
XCODE_DEVELOPER="/Applications/Xcode.app/Contents/Developer"
XCODE_TOOLCHAIN="${XCODE_DEVELOPER}/Toolchains/XcodeDefault.xctoolchain/usr/bin"
SETFILE="${XCODE_DEVELOPER}/usr/bin/SetFile"
DMGBUILD_PYTHON="${REPO_DIR}/.venv/bin/python"

if [[ ! "${VERSION}" =~ ${VERSION_PATTERN} ]]; then
    print -u2 "Native Preview releases require a numeric VERSION; found ${VERSION}"
    exit 1
fi

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    print -u2 'Native Preview packaging currently targets Apple Silicon macOS.'
    exit 1
fi

for required in "${XCODE_TOOLCHAIN}/swiftc" "${XCODE_TOOLCHAIN}/lipo" "${SETFILE}" "${DMGBUILD_PYTHON}"; do
    if [[ ! -x "${required}" ]]; then
        print -u2 "Required packaging tool is missing: ${required}"
        exit 1
    fi
done

if ! "${DMGBUILD_PYTHON}" -c 'import dmgbuild' >/dev/null 2>&1; then
    print -u2 'dmgbuild is missing from .venv. Run scripts/setup-macos.sh first.'
    exit 1
fi

"${NATIVE_DIR}/scripts/build-app.sh"

if [[ ! -d "${APP_BUNDLE}" ]]; then
    print -u2 "Native app bundle was not created: ${APP_BUNDLE}"
    exit 1
fi

APP_PLIST="${APP_BUNDLE}/Contents/Info.plist"
APP_BINARY="${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"
bundle_version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "${APP_PLIST}")
if [[ "${bundle_version}" != "${VERSION}" ]]; then
    print -u2 "Bundle version mismatch: expected ${VERSION}, found ${bundle_version}"
    exit 1
fi

architectures=$("${XCODE_TOOLCHAIN}/lipo" -archs "${APP_BINARY}")
if [[ "${architectures}" != "arm64" ]]; then
    print -u2 "Expected an arm64 native app, found: ${architectures}"
    exit 1
fi
/usr/bin/codesign --verify --deep --strict "${APP_BUNDLE}"

/bin/mkdir -p "${RELEASE_DIR}"
ZIP_PATH="${RELEASE_DIR}/Antarctic-Atlas-v${VERSION}-macOS-arm64.zip"
DMG_PATH="${RELEASE_DIR}/Antarctic-Atlas-v${VERSION}-macOS-arm64.dmg"
/bin/rm -f -- "${ZIP_PATH}" "${ZIP_PATH}.sha256" "${DMG_PATH}" "${DMG_PATH}.sha256"

/usr/bin/ditto -c -k --norsrc --noextattr --noqtn --keepParent \
    "${APP_BUNDLE}" "${ZIP_PATH}"

VERIFY_ROOT=$(mktemp -d /private/tmp/antarctic-atlas-native-release.XXXXXX)
case "${VERIFY_ROOT}" in
    /private/tmp/antarctic-atlas-native-release.*) ;;
    *)
        print -u2 "Unexpected temporary verification path: ${VERIFY_ROOT}"
        exit 1
        ;;
esac
MOUNT_PATH="${VERIFY_ROOT}/mount"
MOUNTED=0

cleanup() {
    if (( MOUNTED != 0 )); then
        /usr/bin/hdiutil detach "${MOUNT_PATH}" -quiet || true
    fi
    [[ -d "${VERIFY_ROOT}" ]] && /bin/rm -rf -- "${VERIFY_ROOT}"
}
trap cleanup EXIT

/usr/bin/ditto -x -k "${ZIP_PATH}" "${VERIFY_ROOT}"
EXTRACTED_APP="${VERIFY_ROOT}/${APP_NAME}.app"
/usr/bin/codesign --verify --deep --strict "${EXTRACTED_APP}"
if [[ "$("${XCODE_TOOLCHAIN}/lipo" -archs "${EXTRACTED_APP}/Contents/MacOS/${APP_NAME}")" != "arm64" ]]; then
    print -u2 'Extracted ZIP application is not arm64.'
    exit 1
fi

background_path="${REPO_DIR}/installer/dmg-background.png"
volume_icon="${REPO_DIR}/installer/antarctic_atlas.icns"
ANTARCTIC_ATLAS_SETFILE="${SETFILE}" \
"${DMGBUILD_PYTHON}" "${REPO_DIR}/scripts/run-dmgbuild.py" \
    --settings "${REPO_DIR}/installer/dmg_settings.py" \
    --app "${APP_BUNDLE}" \
    --background "${background_path}" \
    --volume-icon "${volume_icon}" \
    "Antarctic Atlas ${VERSION} Preview" \
    "${DMG_PATH}"

/usr/bin/hdiutil verify "${DMG_PATH}"
/bin/mkdir -p "${MOUNT_PATH}"
/usr/bin/hdiutil attach -readonly -nobrowse -noverify \
    -mountpoint "${MOUNT_PATH}" "${DMG_PATH}" >/dev/null
MOUNTED=1

MOUNTED_APP="${MOUNT_PATH}/${APP_NAME}.app"
if [[ ! -d "${MOUNTED_APP}" ]]; then
    print -u2 'Native Preview DMG is missing its application bundle.'
    exit 1
fi
if [[ ! -L "${MOUNT_PATH}/Applications" || "$(/usr/bin/readlink "${MOUNT_PATH}/Applications")" != "/Applications" ]]; then
    print -u2 'Native Preview DMG is missing its Applications shortcut.'
    exit 1
fi
visible_entries=$(/usr/bin/find "${MOUNT_PATH}" -mindepth 1 -maxdepth 1 ! -name '.*' \
    -exec /usr/bin/basename {} \; | /usr/bin/sort)
expected_entries=$'Antarctic Atlas Native Preview.app\nApplications'
if [[ "${visible_entries}" != "${expected_entries}" ]]; then
    print -u2 'Native Preview DMG root contains unexpected visible entries.'
    print -u2 -- "${visible_entries}"
    exit 1
fi
/usr/bin/codesign --verify --deep --strict "${MOUNTED_APP}"
/usr/bin/ditto "${MOUNTED_APP}" "${VERIFY_ROOT}/installed.app"
/usr/bin/codesign --verify --deep --strict "${VERIFY_ROOT}/installed.app"

/usr/bin/hdiutil detach "${MOUNT_PATH}" -quiet
MOUNTED=0

(
    cd "${RELEASE_DIR}"
    /usr/bin/shasum -a 256 "${ZIP_PATH:t}" > "${ZIP_PATH:t}.sha256"
    /usr/bin/shasum -a 256 "${DMG_PATH:t}" > "${DMG_PATH:t}.sha256"
    /usr/bin/shasum -a 256 -c "${ZIP_PATH:t}.sha256"
    /usr/bin/shasum -a 256 -c "${DMG_PATH:t}.sha256"
)

print "Built and verified native Preview artifacts in ${RELEASE_DIR}"
print "DMG: ${DMG_PATH}"
print "ZIP: ${ZIP_PATH}"
