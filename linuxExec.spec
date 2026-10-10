# -*- mode: python ; coding: utf-8 -*-
# Build with: pyinstaller linuxExec.spec  ->  dist/pyQCM (single file executable)
# Linux binaries only run on systems with a glibc at least as new as the build machine's,
# so the workflow builds on the oldest available Ubuntu runner

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    # default files copied next to the executable on first launch if missing (see src/frozen_workdir.py)
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
    a.datas,
    [],
    name='pyQCM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # progress messages and errors print to the terminal it is launched from
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
