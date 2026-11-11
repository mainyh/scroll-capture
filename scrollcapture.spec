# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: builds dist/ScrollCapture.exe (one file, windowed).
#   pyinstaller scrollcapture.spec
import re
from pathlib import Path

ROOT = Path(SPECPATH)
SRC = ROOT / "src"
version = re.search(r'__version__\s*=\s*"([^"]+)"', (SRC / "scrollcapture" / "__init__.py").read_text()).group(1)
nums = [int(x) for x in re.findall(r"\d+", version)[:3]] + [0]
while len(nums) < 4:
    nums.insert(-1, 0)
vt = tuple(nums[:4])

version_file = ROOT / "build" / "version_info.txt"
version_file.parent.mkdir(exist_ok=True)
version_file.write_text(f"""
VSVersionInfo(
  ffi=FixedFileInfo(filevers={vt}, prodvers={vt}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'ScrollCapture contributors'),
      StringStruct('FileDescription', 'ScrollCapture - scrolling screenshot tool'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'ScrollCapture'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 김용훈 (mainyh). MIT License.'),
      StringStruct('OriginalFilename', 'ScrollCapture.exe'),
      StringStruct('ProductName', 'ScrollCapture'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""", encoding="utf-8")

a = Analysis(
    [str(SRC / "scrollcapture" / "__main__.py")],
    pathex=[str(SRC)],
    datas=[
        (str(SRC / "scrollcapture" / "resources"), "scrollcapture/resources"),
        (str(ROOT / "LICENSE"), "."),
        (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    ],
    hiddenimports=[],
    excludes=[
        "tkinter", "unittest", "pydoc", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
        "PySide6.QtMultimedia", "PySide6.Qt3DCore", "PySide6.QtCharts", "PySide6.QtPdf",
        "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtOpenGL",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ScrollCapture",
    console=False,
    upx=False,                    # UPX tends to trigger antivirus false positives
    icon=str(SRC / "scrollcapture" / "resources" / "icon.ico"),
    version=str(version_file),
)
