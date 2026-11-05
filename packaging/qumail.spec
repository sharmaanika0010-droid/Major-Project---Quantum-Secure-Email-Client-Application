# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for QuMail (SCRUM-62).

Builds two one-folder apps into dist/:
  dist/QuMail/QuMail.exe        desktop client (windowed, no console)
  dist/QuMail-KM/QuMail-KM.exe  Key Manager simulator (console, port 5000, keybank.csv next to the exe)

Run from the repository root:   pyinstaller packaging/qumail.spec --noconfirm
"""
import os
from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")

# big scientific packages are never needed; keep the build small even if they are installed system-wide
HEAVY = ["numpy", "pandas", "scipy", "matplotlib", "pyarrow", "llvmlite", "numba", "jedi", "IPython",
         "torch", "sklearn", "sympy", "cv2", "notebook", "zmq"]

# customtkinter ships .json themes and fonts that must travel with the exe
ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

client_a = Analysis(
    [os.path.join(SRC, "qumail", "gui", "app.py")],
    pathex=[SRC],
    binaries=ctk_binaries,
    datas=ctk_datas + [(os.path.join(ROOT, ".env.example"), ".")],
    hiddenimports=ctk_hidden + [
        "qumail.crypto.level2", "qumail.crypto.level3", "qumail.crypto.level4",   # loaded dynamically by envelope.load_levels()
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["flask", "pytest", "streamlit", "google", "googleapiclient"] + HEAVY,
    noarchive=False,
)
client_pyz = PYZ(client_a.pure)
client_exe = EXE(
    client_pyz, client_a.scripts, [],
    exclude_binaries=True,
    name="QuMail",
    console=False,                      # GUI app — no black console window
    icon=None,
)
client_coll = COLLECT(client_exe, client_a.binaries, client_a.datas, name="QuMail")

km_a = Analysis(
    [os.path.join(SRC, "km_simulator", "km_simulator.py")],
    pathex=[SRC],
    hiddenimports=["flask", "werkzeug", "jinja2"],
    excludes=["customtkinter", "tkinter", "PIL", "pytest", "streamlit"] + HEAVY,
    noarchive=False,
)
km_pyz = PYZ(km_a.pure)
km_exe = EXE(km_pyz, km_a.scripts, [], exclude_binaries=True, name="QuMail-KM", console=True)
km_coll = COLLECT(km_exe, km_a.binaries, km_a.datas, name="QuMail-KM")
