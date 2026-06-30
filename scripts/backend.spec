# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the self-contained GrantAtlas backend sidecar."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path.cwd()

hiddenimports = (
    collect_submodules("backend")
    + collect_submodules("uvicorn")
    + [
        "fastapi",
        "pydantic",
        "pydantic_settings",
        "multipart",
        "docx",
        "fitz",
        "openpyxl",
        "openai",
        "json_repair",
    ]
)

excludes = [
    "chromadb",
    "matplotlib",
    "numpy.testing",
    "pandas",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "tkinter",
]

a = Analysis(
    [str(ROOT / "scripts" / "backend_server.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="patentagent-backend",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="patentagent-backend",
)
