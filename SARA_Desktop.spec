# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    # CORRECT: All data files are specified here in the Analysis section.
    datas=[('templates', 'templates'), ('static', 'static'), ('sara.db', '.')],
    hiddenimports=[],
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
    name='SARA_Desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # CHANGED: Safer to disable UPX during debugging.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # CORRECTED: Using forward slashes for the icon path is more reliable.
    icon='static/img/rasa1.png',
)

# This part is for directory builds, not needed for --onefile but good practice
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SARA_Desktop',
)

    
