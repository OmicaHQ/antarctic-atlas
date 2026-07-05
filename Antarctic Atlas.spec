# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    'pdfplumber',
    'pandas',
    'numpy',
    'jieba',
    'requests',
    'PIL',
    'pypdfium2',
    'pdfminer.high_level',
    'qt_app.pages.research_universe',
    'qt_app.pages.antarctic_system',
    'qt_app.pages.ai_visualizer',
    'qt_app.pages.mini_research_lab',
    'qt_app.pages.research_directions',
    'qt_app.pages.raw_paper',
]
datas += [('installer/antarctic_atlas.ico', '.')]
datas += [('qt_app', 'qt_app')]
datas += [('locales', 'locales')]
datas += [('Reviews of Geophysics - 2020 - Noble - The Sensitivity of the Antarctic Ice Sheet to a Changing Climate  Past  Present  and.pdf', '.')]
tmp_ret = collect_all('plotly')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['desktop_qt_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['streamlit', 'webview', 'atlas_app'],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='installer/antarctic_atlas.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Antarctic Atlas',
)
