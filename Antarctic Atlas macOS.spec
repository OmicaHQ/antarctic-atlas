# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

app_version = Path('VERSION').read_text(encoding='utf-8').strip()

datas = [
    ('antarctic_atlas.png', '.'),
    ('qt_app/templates', 'qt_app/templates'),
    ('locales', 'locales'),
    ('data', 'data'),
    ('Reviews of Geophysics - 2020 - Noble - The Sensitivity of the Antarctic Ice Sheet to a Changing Climate  Past  Present  and.pdf', '.'),
]
binaries = []
hiddenimports = [
    'pdfplumber',
    'jieba',
    'requests',
    'pypdfium2',
    'pdfminer.high_level',
    'qt_app.pages.research_universe',
    'qt_app.pages.antarctic_system',
    'qt_app.pages.ai_visualizer',
    'qt_app.pages.mini_research_lab',
    'qt_app.pages.research_directions',
    'qt_app.pages.raw_paper',
]


a = Analysis(
    ['desktop_qt_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Antarctic Atlas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
    icon='installer/antarctic_atlas.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Antarctic Atlas',
)

app = BUNDLE(
    coll,
    name='Antarctic Atlas.app',
    icon='installer/antarctic_atlas.icns',
    bundle_identifier='com.omicachow.antarcticatlas',
    info_plist={
        'CFBundleDisplayName': 'Antarctic Atlas',
        'CFBundleName': 'Antarctic Atlas',
        'CFBundleShortVersionString': app_version,
        'CFBundleVersion': app_version,
        'LSMinimumSystemVersion': '13.0',
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
    },
)
