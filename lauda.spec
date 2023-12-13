# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['lauda.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        (r'res\lauda_app_icon.ico', 'res'),
        (r'res\programm_data.csv', 'res'),
        (r'res\ush_400.pdf', 'res'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LAUDA_Thermostat',
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
    icon=r'res\lauda_app_icon.ico'
)
