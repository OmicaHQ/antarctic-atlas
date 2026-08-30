#!/usr/bin/env python3
"""Run dmgbuild with the real Xcode SetFile binary.

Some macOS installations leave /usr/bin/SetFile behind an unaccepted Command
Line Tools license shim even when a complete Xcode.app is usable. dmgbuild uses
that absolute path for Finder flags, so substitute the verified Xcode binary.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess

from dmgbuild import build_dmg
import dmgbuild.core


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument("--background", required=True)
    parser.add_argument("--volume-icon", required=True)
    parser.add_argument("volume_name")
    parser.add_argument("output")
    args = parser.parse_args()

    setfile = Path(os.environ["ANTARCTIC_ATLAS_SETFILE"]).resolve()
    if not setfile.is_file() or not os.access(setfile, os.X_OK):
        raise SystemExit(f"Xcode SetFile is unavailable: {setfile}")

    original_call = subprocess.call

    def reliable_call(command, *call_args, **call_kwargs):
        resolved_command = list(command)
        if resolved_command and resolved_command[0] == "/usr/bin/SetFile":
            resolved_command[0] = str(setfile)
        result = original_call(resolved_command, *call_args, **call_kwargs)
        if resolved_command and resolved_command[0] == str(setfile) and result != 0:
            raise RuntimeError(f"SetFile failed with status {result}")
        return result

    dmgbuild.core.subprocess.call = reliable_call
    build_dmg(
        args.output,
        args.volume_name,
        args.settings,
        defines={
            "app": args.app,
            "background": args.background,
            "volume_icon": args.volume_icon,
        },
    )


if __name__ == "__main__":
    main()
