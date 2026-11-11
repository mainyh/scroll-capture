# Third-Party Notices

ScrollCapture is licensed under the MIT License (see `LICENSE`).
The release executable bundles the following third-party components, each under its own license.

| Component | License | Project |
|---|---|---|
| Python | PSF License 2.0 | https://www.python.org/ |
| Qt 6 / PySide6 (Qt for Python) | LGPL-3.0 | https://www.qt.io/qt-for-python |
| NumPy | BSD-3-Clause | https://numpy.org/ |
| Pillow | MIT-CMU (HPND) | https://python-pillow.org/ |
| python-mss | MIT | https://github.com/BoboTiG/python-mss |
| Pretendard (font) | SIL Open Font License 1.1 | https://github.com/orioncactus/pretendard |
| PyInstaller bootloader | GPL-2.0 with bootloader exception | https://pyinstaller.org/ |

## Qt / PySide6 (LGPL-3.0)

ScrollCapture uses the Qt libraries through PySide6 under the GNU Lesser General Public
License v3. Qt is dynamically linked (the Qt DLLs are unpacked next to the program at
runtime), so you can replace them with your own build. The Qt and PySide6 source code is
available at https://code.qt.io/ and https://download.qt.io/official_releases/QtForPython/.
The full LGPL-3.0 text: https://www.gnu.org/licenses/lgpl-3.0.html

## Pretendard

Copyright (c) 2021, Kil Hyung-jin (https://github.com/orioncactus/pretendard),
with Reserved Font Name Pretendard. Licensed under the SIL Open Font License, Version 1.1.
The unmodified font files are bundled in `src/scrollcapture/resources/fonts/` together with
the full license text (`OFL.txt`).

## PyInstaller

The executable is produced with PyInstaller. Its bootloader is GPL-2.0 licensed with an
exception that allows distributing the resulting executable under any license.
See https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

## NumPy

Copyright (c) 2005-2025, NumPy Developers. BSD-3-Clause.
https://github.com/numpy/numpy/blob/main/LICENSE.txt
NumPy wheels bundle OpenBLAS (BSD-3-Clause) and related runtime libraries; see the
NumPy license file for details.

## Pillow

Copyright © 1997-2011 by Secret Labs AB, © 1995-2011 by Fredrik Lundh and contributors,
© 2010 by Jeffrey A. Clark and contributors. MIT-CMU License.
https://github.com/python-pillow/Pillow/blob/main/LICENSE
Pillow wheels bundle libjpeg-turbo, libpng, zlib and other libraries under their own
permissive licenses (listed in the Pillow license file).

## python-mss

Copyright (c) 2013-2025, Mickaël 'Tiger-222' Schoentgen & contributors. MIT License.
https://github.com/BoboTiG/python-mss/blob/main/LICENSE.txt

## Python

Copyright © 2001 Python Software Foundation. PSF License Agreement.
https://docs.python.org/3/license.html
