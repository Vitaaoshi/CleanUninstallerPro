# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['bg_service.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        'winreg', 'win32api', 'win32con',
        'watchdog', 'watchdog.observers', 'watchdog.events',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'core.scanner', 'core.uninstaller', 'core.residual_scanner',
        'core.junk_cleaner', 'core.software_classifier',
        'gui.main_window', 'gui.residual_dialog',
        'utils.registry', 'utils.file_utils',
    ],
    noarchive=False,
    optimize=0,
    key='CleanUninstallerPro2026',
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CleanUninstallerPro_Bg',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)