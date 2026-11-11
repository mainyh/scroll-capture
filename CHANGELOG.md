# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- Main window hint now reads "Press Start Capture, then pick a window".
- Release workflow can sign `ScrollCapture.exe` through SignPath (SignPath Foundation OSS program);
  added `CODE_SIGNING_POLICY.md` and the SignPath artifact configuration.

## [0.9.1] - 2026-11-11

### Fixed
- Multi-monitor (especially mixed DPI): the window highlight in the picker could be drawn at
  the wrong position/size. Each overlay is now created on its own monitor, pinned to the
  monitor's exact physical rectangle, and maps coordinates from its actual native window rect.
  Monitors are matched to Qt screens by device name or position instead of list order.

### Changed
- Clearer picker highlight: thicker border with a dark halo, light tint inside the selected
  window, and the hint shown only on the monitor under the cursor.

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

[0.9.1]: https://github.com/mainyh/scroll-capture/releases/tag/v0.9.1
[0.9.0]: https://github.com/mainyh/scroll-capture/releases/tag/v0.9.0
