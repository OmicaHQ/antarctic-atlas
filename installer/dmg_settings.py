"""Deterministic Finder layout for the Antarctic Atlas drag-to-install DMG."""

from pathlib import Path


application = Path(defines["app"]).resolve()  # noqa: F821 - provided by dmgbuild
if not application.is_dir() or application.suffix != ".app":
    raise ValueError(f"Invalid application bundle: {application}")

app_name = application.name

format = "UDZO"
filesystem = "HFS+"
files = [str(application)]
symlinks = {"Applications": "/Applications"}
icon = str(Path(defines["volume_icon"]).resolve())  # noqa: F821

background = str(Path(defines["background"]).resolve())  # noqa: F821
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
window_rect = ((120, 120), (680, 440))
default_view = "icon-view"
show_icon_preview = False
include_icon_view_settings = True
include_list_view_settings = False

arrange_by = None
grid_offset = (0, 0)
grid_spacing = 90
scroll_position = (0, 0)
label_pos = "bottom"
text_size = 14
icon_size = 112
icon_locations = {
    app_name: (170, 220),
    "Applications": (510, 220),
}
