"""Minimal two-language (Korean / English) string table."""
from __future__ import annotations

_lang = "en"

# key: (Korean, English)
STRINGS: dict[str, tuple[str, str]] = {
    # main window
    "app.tagline": ("스크롤 캡쳐", "Scrolling screenshot"),
    "main.no_target": ("캡쳐할 창을 선택하세요", "Pick a window to capture"),
    "main.no_target_sub": ("창 선택 후 캡쳐 시작을 누르세요", "Then press Start Capture"),
    "main.area_auto": ("영역 {w}×{h} (자동)", "Area {w}×{h} (auto)"),
    "main.area_manual": ("영역 {w}×{h} (수동)", "Area {w}×{h} (manual)"),
    "main.pick_window": ("창 선택", "Pick Window"),
    "main.select_area": ("영역 지정", "Select Area"),
    "main.window_list": ("목록", "List"),
    "main.format": ("저장 형식", "Format"),
    "main.save_to": ("저장 폴더", "Save to"),
    "main.options": ("옵션", "Options"),
    "main.opt_top": ("맨 위부터", "Start from top"),
    "main.opt_instant": ("바로 저장", "Save instantly"),
    "main.start": ("캡쳐 시작 ({key})", "Start Capture ({key})"),
    "main.settings": ("설정", "Settings"),
    "main.browse": ("폴더 선택", "Choose folder"),
    "main.no_windows": ("캡쳐할 수 있는 창이 없습니다", "No windows available"),
    # status
    "status.ready": ("준비됨 · 캡쳐 중 Esc로 중지", "Ready · Press Esc to stop while capturing"),
    "status.detecting": ("스크롤 영역 감지 중…", "Detecting scroll area…"),
    "status.target_set": ("대상 창: {title}", "Target: {title}"),
    "status.done": ("캡쳐 완료 · {w}×{h}", "Capture complete · {w}×{h}"),
    "status.cancelled": ("캡쳐를 취소했습니다", "Capture cancelled"),
    "status.saved": ("저장됨: {file}", "Saved: {file}"),
    "status.hotkey_fail": ("단축키 {key} 등록 실패 (다른 프로그램이 사용 중)",
                           "Could not register hotkey {key} (in use by another app)"),
    # picker
    "pick.hint_window": ("클릭: 창 선택 · 드래그: 영역 직접 지정 · Esc: 취소",
                         "Click: select · Drag: custom area · Esc: cancel"),
    "pick.hint_area": ("드래그해서 캡쳐할 영역을 지정하세요 · Esc: 취소",
                       "Drag to select the area to capture · Esc: cancel"),
    # HUD
    "hud.capturing": ("캡쳐 중", "Capturing"),
    "hud.preparing": ("준비 중", "Preparing"),
    "hud.frames": ("프레임", "Frames"),
    "hud.height": ("높이", "Height"),
    "hud.max": ("최대 {n} px", "Max {n} px"),
    "hud.stop": ("중지 (Esc)", "Stop (Esc)"),
    "hud.cancel": ("취소", "Cancel"),
    "hud.saved": ("저장됨", "Saved"),
    # editor
    "ed.title": ("ScrollCapture — 결과 ({w} × {h})", "ScrollCapture — Result ({w} × {h})"),
    "ed.crop": ("크롭", "Crop"),
    "ed.undo": ("실행 취소", "Undo"),
    "ed.original": ("원본", "Original"),
    "ed.fit": ("맞춤", "Fit"),
    "ed.apply": ("적용 (Enter)", "Apply (Enter)"),
    "ed.cancel_crop": ("취소 (Esc)", "Cancel (Esc)"),
    "ed.save_section": ("저장", "Save"),
    "ed.save": ("저장 (Ctrl+S)", "Save (Ctrl+S)"),
    "ed.save_as": ("다른 이름으로…", "Save As…"),
    "ed.copy": ("복사 (Ctrl+C)", "Copy (Ctrl+C)"),
    "ed.status": ("배율 {zoom}% · 이미지 {w}×{h}", "Zoom {zoom}% · Image {w}×{h}"),
    "ed.status_crop": ("배율 {zoom}% · 크롭 영역 {cw}×{ch} · 이미지 {w}×{h}",
                       "Zoom {zoom}% · Crop {cw}×{ch} · Image {w}×{h}"),
    "ed.crop_hint": ("드래그해서 크롭 영역을 지정하세요", "Drag to select the crop area"),
    "ed.copied": ("클립보드에 복사했습니다", "Copied to clipboard"),
    "ed.copy_large": ("이미지가 매우 커서 일부 프로그램에는 붙여넣기가 안 될 수 있습니다.",
                      "The image is very large; some apps may not accept it from the clipboard."),
    "ed.unsaved": ("저장하지 않은 캡쳐가 있습니다. 닫을까요?", "This capture has not been saved. Close anyway?"),
    "ed.saved_with_gaps": ("일부 구간에서 겹침을 찾지 못해 이음새가 있을 수 있습니다.",
                           "Overlap could not be found in some places; the image may contain seams."),
    # dialogs / errors
    "dlg.png": ("PNG 이미지 (*.png)", "PNG image (*.png)"),
    "dlg.jpg": ("JPG 이미지 (*.jpg *.jpeg)", "JPG image (*.jpg *.jpeg)"),
    "dlg.save_failed": ("저장 실패: {err}", "Save failed: {err}"),
    "err.no_scroll": ("스크롤할 내용이 없습니다. 현재 화면만 저장합니다.",
                      "Nothing to scroll. Saving the visible area only."),
    "err.elevated": ("관리자 권한으로 실행 중인 창은 캡쳐할 수 없습니다.\nScrollCapture를 관리자 권한으로 실행하세요.",
                     "Can't capture a window running as administrator.\nRun ScrollCapture as administrator."),
    "err.window_gone": ("대상 창을 찾을 수 없습니다. 다시 선택하세요.", "The target window is gone. Please pick it again."),
    "err.jpg_limit": ("JPG는 최대 65,535px까지만 저장할 수 있습니다 (현재 {h}px).\nPNG로 저장하거나 여러 장으로 나눠 저장하세요.",
                      "JPG is limited to 65,535 px (this image is {h} px).\nSave as PNG or split into several files."),
    "err.jpg_png": ("PNG로 저장", "Save as PNG"),
    "err.jpg_split": ("나눠 저장", "Split"),
    "err.capture_failed": ("캡쳐 중 오류가 발생했습니다:\n{err}", "Capture failed:\n{err}"),
    "err.unexpected": ("예기치 않은 오류가 발생했습니다:\n{err}\n\n로그: {log}",
                       "An unexpected error occurred:\n{err}\n\nLog: {log}"),
    "warn.max_height": ("최대 높이에 도달해 캡쳐를 중지했습니다.", "Capture stopped: maximum height reached."),
    "warn.already_running": ("ScrollCapture가 이미 실행 중입니다.", "ScrollCapture is already running."),
    # settings
    "set.title": ("설정", "Settings"),
    "set.tab_general": ("일반", "General"),
    "set.tab_capture": ("캡쳐", "Capture"),
    "set.tab_hotkeys": ("단축키", "Hotkeys"),
    "set.tab_about": ("정보", "About"),
    "set.language": ("언어", "Language"),
    "set.lang_system": ("시스템 설정", "System"),
    "set.lang_restart": ("언어 변경은 프로그램을 다시 시작하면 적용됩니다.", "Restart ScrollCapture to apply the language change."),
    "set.save_dir": ("저장 폴더", "Save folder"),
    "set.format": ("기본 형식", "Default format"),
    "set.jpg_quality": ("JPG 품질", "JPG quality"),
    "set.pattern": ("파일명 패턴", "File name pattern"),
    "set.pattern_help": ("{title} 창 제목 · {date} 날짜 · {time} 시각 · {datetime} 날짜_시각",
                         "{title} window title · {date} date · {time} time · {datetime} date_time"),
    "set.instant": ("캡쳐 후 바로 저장 (편집 창 생략)", "Save right after capture (skip editor)"),
    "set.open_folder": ("저장 후 폴더 열기", "Open folder after saving"),
    "set.metadata": ("PNG에 캡쳐 정보 기록 (창 제목, 시각)", "Embed capture info in PNG (window title, time)"),
    "set.start_top": ("맨 위부터 시작", "Start from top"),
    "set.scroll_amount": ("스크롤 양", "Scroll amount"),
    "set.scroll_auto": ("자동", "Automatic"),
    "set.scroll_notches": ("휠 {n}칸", "{n} wheel notches"),
    "set.delay": ("프레임 대기 시간", "Frame delay"),
    "set.max_height": ("최대 높이", "Maximum height"),
    "set.sticky": ("고정 헤더/푸터 제거", "Remove sticky header/footer"),
    "set.hotkey_capture": ("캡쳐 시작", "Start capture"),
    "set.hotkey_stop": ("중지", "Stop"),
    "set.hotkey_note": ("Esc 키는 캡쳐 중에만 사용됩니다.", "Esc is only taken while capturing."),
    "set.version": ("버전 {v}", "Version {v}"),
    "set.license": ("MIT 라이선스로 배포되는 오픈소스입니다.", "Open source under the MIT License."),
    "set.notices": ("오픈소스 고지 보기", "Open-source notices"),
    "set.github": ("GitHub에서 보기", "View on GitHub"),
    "set.ok": ("확인", "OK"),
    "set.cancel": ("취소", "Cancel"),
}


def set_language(code: str) -> str:
    """``code`` is 'ko', 'en' or 'system'. Returns the effective language."""
    global _lang
    if code == "system":
        try:
            from PySide6.QtCore import QLocale
            code = "ko" if QLocale.system().language() == QLocale.Language.Korean else "en"
        except Exception:
            code = "en"
    _lang = "ko" if code == "ko" else "en"
    return _lang


def language() -> str:
    return _lang


def tr(key: str, /, **kw) -> str:
    pair = STRINGS.get(key)
    if pair is None:
        return key
    text = pair[0] if _lang == "ko" else pair[1]
    return text.format(**kw) if kw else text
