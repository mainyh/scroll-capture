# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.9.0] - 2026-11-11

First public beta.

### Added
- Scrolling capture of any Windows app: pick a window by clicking, or drag a custom area.
- Automatic scroll-area detection (child window under the cursor + test scroll).
- Seamless stitching: per-row band hashing with tolerant fallback, sticky header/footer removal,
  floating-element handling, scrollbar trimming.
- Progress panel (excluded from capture) with Stop (`Esc`) and Cancel.
- Result editor with crop (8 handles), undo, original, fit/100% zoom, save, save as, copy.
- PNG (default) and JPG export; PNG capture metadata; JPG height limit handling (save as PNG or split).
- Global hotkey `Ctrl+Shift+S` (configurable), settings dialog, Korean/English UI.
- Pretendard UI font (bundled, SIL OFL 1.1), consistent light/dark design tokens and line icons.
- Single-instance app, log file in `%APPDATA%\ScrollCapture`.
- Portable single-file `ScrollCapture.exe` built with PyInstaller; GitHub Actions CI and release workflow.

[0.9.0]: https://github.com/mainyh/scroll-capture/releases/tag/v0.9.0
