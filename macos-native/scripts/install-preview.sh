#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
REPO_DIR="${SCRIPT_DIR:h:h}"
SOURCE_APP="${REPO_DIR}/dist-native/Antarctic Atlas Native Preview.app"
TARGET_APP="/Applications/Antarctic Atlas Native Preview.app"

if [[ ! -d "${SOURCE_APP}" ]]; then
    echo "Build the native preview before installing it." >&2
    exit 1
fi

if [[ "${TARGET_APP}" != "/Applications/Antarctic Atlas Native Preview.app" ]]; then
    echo "Refusing to replace an unexpected application path." >&2
    exit 1
fi

rm -rf "${TARGET_APP}"
cp -R "${SOURCE_APP}" "${TARGET_APP}"
/usr/bin/codesign --verify --deep --strict --verbose=2 "${TARGET_APP}"
echo "Installed ${TARGET_APP}"
