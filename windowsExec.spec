# -*- mode: python ; coding: utf-8 -*-

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
        'pandas', 'numpy', 'scipy', 'matplotlib', 
        'matplotlib.backends.backend_tkagg', 
        'matplotlib.backends.backend_pdf', 
        'matplotlib.backends.backend_agg', 
        'xlrd', 'openpyxl', 'datetime'
    ],
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
    a.zipfiles, # Critical for onefile stability
    a.datas,
    [],
    name='pyQCMWindows',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)