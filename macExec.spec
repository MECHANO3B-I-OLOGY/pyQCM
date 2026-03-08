# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('plot_opts', 'plot_opts'),
        ('offset_data', 'offset_data'),
        ('sample_generations', 'sample_generations'),
        ('res', 'res'),
    ],
    hiddenimports=[
        'pandas', 
        'numpy', 
        'scipy', 
        'matplotlib', 
        'matplotlib.backends.backend_tkagg', 
        'matplotlib.backends.backend_pdf', 
        'matplotlib.backends.backend_agg', 
        'xlrd', 
        'openpyxl', 
        'datetime'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pyQCM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Shows the Terminal window alongside your app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# This creates the pyQCM.app folder for macOS
app = BUNDLE(
    exe,
    name='pyQCM.app',
    icon=None,
    bundle_identifier='com.pyqcm.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleBundleName': 'pyQCM',
        'NSHighResolutionCapable': 'True',
    },
)