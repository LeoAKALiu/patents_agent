# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the PatentAgent backend sidecar.

Produces an onedir bundle named `patentagent-backend` containing the
FastAPI app plus all runtime deps (fastapi, uvicorn, pydantic, python-docx,
PyMuPDF, openpyxl, openai). chromadb is excluded — it is an optional
enhancement (backend/app/rag.py falls back to LocalVectorIndex) and its
large native dependency tree would bloat and destabilise the bundle.

Build:  pyinstaller scripts/backend.spec --noconfirm --distpath build/backend
"""
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

block_cipher = None

# Collect all backend submodules so PyInstaller's static analysis does not
# miss dynamically-imported modules (e.g. router modules referenced by name).
hiddenimports = collect_submodules("backend") + [
    "uvicorn.logging",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "email.mime.multipart",
    "email.mime.text",
]

# Pydantic / fastapi need their package metadata at runtime.
datas = []
for pkg in ("fastapi", "pydantic", "pydantic_core", "starlette", "uvicorn"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    ["backend_server.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Optional RAG backend — rag.py falls back to LocalVectorIndex.
        "chromadb",
        "pytest",
        "tests",
        # Anaconda ships a large default env; exclude everything the backend
        # does not import so the bundle stays small and free of Qt conflicts.
        # NOTE: httpx must stay — it is an openai runtime dependency.
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "matplotlib",
        "tkinter",
        "zmq",
        "IPython",
        "jupyter",
        "notebook",
        "ipykernel",
        "nbconvert",
        "nbformat",
        "pandas",
        "numpy",
        "scipy",
        "sklearn",
        "sympy",
        "PIL",
        "cv2",
        "skimage",
        "bokeh",
        "plotly",
        "seaborn",
        "tornado",
        "sqlalchemy",
        "psycopg2",
        "pymysql",
        "black",
        "yapf",
        "isort",
        "flake8",
        "mypy",
        "sphinx",
        "pydocstyle",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="patentagent-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    target_arch="arm64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="patentagent-backend",
)
