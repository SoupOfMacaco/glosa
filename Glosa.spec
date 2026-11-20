# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller:  pyinstaller Glosa.spec --noconfirm
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = [("app/data", "app/data"), ("assets", "assets")]
binaries = []
hiddenimports = []

for pkg in ("winrt",):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
datas += collect_data_files("spellchecker")

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "tkinter", "numpy", "setuptools", "unittest", "pydoc",
        "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtPdf", "PySide6.QtOpenGL",
    ],
    noarchive=False,
)

# Quitar partes de Qt que la app no usa (reduce mucho el tamaño)
DROP = (
    "opengl32sw.dll", "Qt6Pdf", "Qt6Qml", "Qt6Quick", "Qt6Network", "Qt6OpenGL", "Qt6VirtualKeyboard",
    "libcrypto-3-x64", "libssl-3-x64", "qtuiotouchplugin", "qpdf", "qnetworklistmanager", "qtls",
    "PySide6\\translations", "PySide6/translations",
)
a.binaries = [b for b in a.binaries if not any(d in b[0] or d in b[1] for d in DROP)]
a.datas = [d for d in a.datas if not any(x in d[0] for x in DROP)]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Glosa",
    icon="assets/icon.ico",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Glosa", upx=False)
