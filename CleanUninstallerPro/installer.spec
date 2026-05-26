# -*- mode: python ; coding: utf-8 -*-

import os

app_exe = os.path.join(SPECPATH, "dist", "CleanUninstallerPro.exe")
bg_exe = os.path.join(SPECPATH, "dist", "CleanUninstallerPro_Bg.exe")

datas = []
if os.path.isfile(app_exe):
    datas.append((app_exe, "app_data"))
if os.path.isfile(bg_exe):
    datas.append((bg_exe, "app_data"))

a = Analysis(
    ['setup_installer.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.ttk',
        'win32com', 'win32com.client', 'pythoncom',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6', 'watchdog', 'psutil',
        'core', 'gui', 'utils',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CleanUninstallerPro_Setup',
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
    uac_admin=True,
)