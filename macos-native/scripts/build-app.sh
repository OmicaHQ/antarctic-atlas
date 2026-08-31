#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
NATIVE_DIR="${SCRIPT_DIR:h}"
REPO_DIR="${NATIVE_DIR:h}"
BUILD_DIR="${NATIVE_DIR}/.build-native"
DIST_DIR="${REPO_DIR}/dist-native"
APP_NAME="Antarctic Atlas Native Preview"
APP_BUNDLE="${DIST_DIR}/${APP_NAME}.app"
CONTENTS_DIR="${APP_BUNDLE}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"
DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
SWIFTC_BIN="${DEVELOPER_DIR}/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
SDK_PATH="${DEVELOPER_DIR}/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
PAPER_NAME="Reviews of Geophysics - 2020 - Noble - The Sensitivity of the Antarctic Ice Sheet to a Changing Climate  Past  Present  and.pdf"

if [[ ! -x "${SWIFTC_BIN}" ]]; then
    echo "Swift compiler was not found at ${SWIFTC_BIN}" >&2
    exit 1
fi

if [[ ! -f "${REPO_DIR}/${PAPER_NAME}" ]]; then
    echo "Bundled paper is missing from the repository." >&2
    exit 1
fi

mkdir -p "${BUILD_DIR}"
SOURCE_FILES=("${NATIVE_DIR}/Sources/AntarcticAtlas/"*.swift)
"${SWIFTC_BIN}" \
    -parse-as-library \
    -whole-module-optimization \
    -O \
    -target arm64-apple-macosx15.0 \
    -sdk "${SDK_PATH}" \
    "${SOURCE_FILES[@]}" \
    -o "${BUILD_DIR}/AntarcticAtlas"

if [[ "${APP_BUNDLE}" != "${DIST_DIR}/Antarctic Atlas Native Preview.app" ]]; then
    echo "Refusing to replace an unexpected app path: ${APP_BUNDLE}" >&2
    exit 1
fi

rm -rf "${APP_BUNDLE}"
mkdir -p "${MACOS_DIR}" "${RESOURCES_DIR}/data"

cp "${BUILD_DIR}/AntarcticAtlas" "${MACOS_DIR}/${APP_NAME}"
cp "${NATIVE_DIR}/Info.plist" "${CONTENTS_DIR}/Info.plist"
cp "${REPO_DIR}/installer/antarctic_atlas.icns" "${RESOURCES_DIR}/AppIcon.icns"
cp "${NATIVE_DIR}/Sources/AntarcticAtlas/Resources/AntarcticUniverseBackground.png" "${RESOURCES_DIR}/AntarcticUniverseBackground.png"
cp "${REPO_DIR}/${PAPER_NAME}" "${RESOURCES_DIR}/Antarctic-Ice-Sheet-Review.pdf"
cp "${REPO_DIR}/data/research_areas.json" "${RESOURCES_DIR}/data/research_areas.json"
cp "${REPO_DIR}/data/topics.json" "${RESOURCES_DIR}/data/topics.json"
cp "${REPO_DIR}/data/keywords.json" "${RESOURCES_DIR}/data/keywords.json"

/usr/bin/codesign --force --deep --sign - "${APP_BUNDLE}"
/usr/bin/codesign --verify --deep --strict --verbose=2 "${APP_BUNDLE}"

echo "Built ${APP_BUNDLE}"
