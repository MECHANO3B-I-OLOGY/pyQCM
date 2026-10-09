# -*- mode: python ; coding: utf-8 -*-
# Build with: pyinstaller macExec.spec  ->  dist/pyQCM.app
# onedir (EXE + COLLECT) inside the .app, onefile .app bundles are deprecated by PyInstaller 6 and blocked in 7

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    # default files copied into the user's data folder on first launch (see src/frozen_workdir.py)
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
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pyQCM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False, # .app bundles do not get a terminal; run pyQCM.app/Contents/MacOS/pyQCM from Terminal to see output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None, # native arch of the build machine, the workflow builds arm64 and x86_64 separately
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='pyQCM',
)

app = BUNDLE(
    coll,
    name='pyQCM.app',
    icon=None,
    bundle_identifier='com.pyqcm.app',
    info_plist={
        'CFBundleName': 'pyQCM',
        'CFBundleDisplayName': 'pyQCM',
        'CFBundleShortVersionString': '1.4.0',
        'NSHighResolutionCapable': 'True',
    },
)
