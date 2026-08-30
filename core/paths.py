"""macOS per-user paths for Antarctic Atlas.

Keep mutable settings and caches outside the source tree and outside packaged
application resources. Environment overrides make headless tests and managed
deployments deterministic without changing the user's real profile.
"""

import os
from pathlib import Path
from typing import Mapping, Optional


APP_DISPLAY_NAME = "Antarctic Atlas"
CONFIG_DIR_ENV = "ANTARCTIC_ATLAS_CONFIG_DIR"
CACHE_DIR_ENV = "ANTARCTIC_ATLAS_CACHE_DIR"


def _environment(environ: Optional[Mapping[str, str]] = None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def _home(home: Optional[Path] = None) -> Path:
    return Path.home() if home is None else Path(home)


def app_config_dir(
    environ: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    """Return the macOS directory for persistent user settings."""

    env = _environment(environ)
    override = env.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()

    return _home(home) / "Library" / "Application Support" / APP_DISPLAY_NAME


def app_cache_dir(
    environ: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Path:
    """Return the macOS directory for replaceable application caches."""

    env = _environment(environ)
    override = env.get(CACHE_DIR_ENV)
    if override:
        return Path(override).expanduser()

    return _home(home) / "Library" / "Caches" / APP_DISPLAY_NAME


def settings_path() -> Path:
    return app_config_dir() / "settings.json"


def paper_cache_path() -> Path:
    return app_cache_dir() / "pages.pkl"
