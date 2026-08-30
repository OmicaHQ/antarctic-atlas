"""Application version lookup that works in source and packaged builds."""

import re

from .data import resource_path


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def app_version() -> str:
    try:
        value = resource_path("VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
    return value if _SEMVER.fullmatch(value) else "0.0.0"
