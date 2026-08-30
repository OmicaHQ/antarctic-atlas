from pathlib import Path

from core.paths import app_cache_dir, app_config_dir


def test_macos_uses_library_directories():
    home = Path("/Users/example")
    assert app_config_dir(environ={}, home=home) == (
        home / "Library" / "Application Support" / "Antarctic Atlas"
    )
    assert app_cache_dir(environ={}, home=home) == (
        home / "Library" / "Caches" / "Antarctic Atlas"
    )


def test_environment_overrides_take_priority():
    env = {
        "ANTARCTIC_ATLAS_CONFIG_DIR": "/tmp/atlas-config",
        "ANTARCTIC_ATLAS_CACHE_DIR": "/tmp/atlas-cache",
    }
    assert app_config_dir(environ=env, home=Path("/Users/example")) == Path(
        "/tmp/atlas-config"
    )
    assert app_cache_dir(environ=env, home=Path("/Users/example")) == Path(
        "/tmp/atlas-cache"
    )
