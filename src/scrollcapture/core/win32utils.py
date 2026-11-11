"""Thin ctypes wrappers around the Win32 APIs ScrollCapture needs.

All coordinates are *physical* screen pixels. The process is expected to be
Per-Monitor-DPI-Aware v2 (Qt 6 sets this by default; see ``ensure_dpi_awareness``
for non-Qt use such as tests and scripts).
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import time
from dataclasses import dataclass

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")

# --------------------------------------------------------------------------- constants
WHEEL_DELTA = 120
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
VK_MENU = 0x12
VK_ESCAPE = 0x1B

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_CHILD = 0x40000000

SW_RESTORE = 9
DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPTRANSPARENT = 0x0004
WDA_NONE = 0x0
WDA_EXCLUDEFROMCAPTURE = 0x11

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20

_SKIP_CLASSES = {
    "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
    "Windows.UI.Core.CoreWindow", "XamlExplorerHostIslandWindow",
}


# --------------------------------------------------------------------------- structures
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT),
                ("dwFlags", wt.DWORD), ("szDevice", wt.WCHAR * 32)]


# --------------------------------------------------------------------------- signatures
user32.GetWindowLongW.restype = wt.LONG
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.ChildWindowFromPointEx.restype = wt.HWND
user32.ChildWindowFromPointEx.argtypes = [wt.HWND, wt.POINT, wt.UINT]
user32.GetAncestor.restype = wt.HWND
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SetWindowDisplayAffinity.argtypes = [wt.HWND, wt.DWORD]
user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
user32.MonitorFromPoint.restype = wt.HMONITOR
user32.MonitorFromPoint.argtypes = [wt.POINT, wt.DWORD]
user32.GetForegroundWindow.restype = wt.HWND
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
advapi32.GetTokenInformation.argtypes = [wt.HANDLE, ctypes.c_int, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]

WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)


# --------------------------------------------------------------------------- data types
@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.right) // 2, (self.top + self.bottom) // 2

    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom

    def intersect(self, o: "Rect") -> "Rect":
        return Rect(max(self.left, o.left), max(self.top, o.top),
                    min(self.right, o.right), min(self.bottom, o.bottom))

    def intersects(self, o: "Rect") -> bool:
        return not self.intersect(o).is_empty()

    def translated(self, dx: int, dy: int) -> "Rect":
        return Rect(self.left + dx, self.top + dy, self.right + dx, self.bottom + dy)

    @staticmethod
    def from_points(x0: int, y0: int, x1: int, y1: int) -> "Rect":
        return Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    @staticmethod
    def _from_win(r: wt.RECT) -> "Rect":
        return Rect(r.left, r.top, r.right, r.bottom)


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    class_name: str
    pid: int
    exe_path: str
    rect: Rect

    @property
    def exe_name(self) -> str:
        return os.path.basename(self.exe_path) if self.exe_path else ""


@dataclass(frozen=True)
class MonitorInfo:
    device: str
    rect: Rect
    work: Rect


# --------------------------------------------------------------------------- DPI
def ensure_dpi_awareness() -> None:
    """Make the process Per-Monitor-v2 DPI aware (no-op if already set)."""
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.WinDLL("shcore").SetProcessDpiAwareness(2)
        except Exception:
            pass


# --------------------------------------------------------------------------- windows
def is_window(hwnd: int) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(wt.HWND(hwnd)))


def window_title(hwnd: int) -> str:
    n = user32.GetWindowTextLengthW(wt.HWND(hwnd))
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(wt.HWND(hwnd), buf, n + 1)
    return buf.value


def class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(wt.HWND(hwnd), buf, 256)
    return buf.value


def window_pid(hwnd: int) -> int:
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(wt.HWND(hwnd), ctypes.byref(pid))
    return pid.value


def process_path(pid: int) -> str:
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        size = wt.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(h)


def is_process_elevated(pid: int) -> bool | None:
    """True/False, or None when it cannot be determined (usually means elevated)."""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        tok = wt.HANDLE()
        if not advapi32.OpenProcessToken(h, TOKEN_QUERY, ctypes.byref(tok)):
            return None
        try:
            elev = wt.DWORD()
            ret = wt.DWORD()
            if not advapi32.GetTokenInformation(tok, TokenElevation, ctypes.byref(elev),
                                                ctypes.sizeof(elev), ctypes.byref(ret)):
                return None
            return bool(elev.value)
        finally:
            kernel32.CloseHandle(tok)
    finally:
        kernel32.CloseHandle(h)


def current_process_elevated() -> bool:
    return bool(is_process_elevated(os.getpid()))


def window_rect(hwnd: int) -> Rect:
    """Visible window bounds (without the invisible resize borders on Win10+)."""
    r = wt.RECT()
    if dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS,
                                    ctypes.byref(r), ctypes.sizeof(r)) == 0:
        return Rect._from_win(r)
    user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
    return Rect._from_win(r)


def raw_window_rect(hwnd: int) -> Rect:
    r = wt.RECT()
    user32.GetWindowRect(wt.HWND(hwnd), ctypes.byref(r))
    return Rect._from_win(r)


def client_rect(hwnd: int) -> Rect:
    r = wt.RECT()
    user32.GetClientRect(wt.HWND(hwnd), ctypes.byref(r))
    pt = wt.POINT(0, 0)
    user32.ClientToScreen(wt.HWND(hwnd), ctypes.byref(pt))
    return Rect(pt.x, pt.y, pt.x + r.right, pt.y + r.bottom)


def is_cloaked(hwnd: int) -> bool:
    v = wt.DWORD()
    if dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), DWMWA_CLOAKED,
                                    ctypes.byref(v), ctypes.sizeof(v)) == 0:
        return v.value != 0
    return False


def is_minimized(hwnd: int) -> bool:
    return bool(user32.IsIconic(wt.HWND(hwnd)))


def window_info(hwnd: int) -> WindowInfo:
    pid = window_pid(hwnd)
    return WindowInfo(hwnd=hwnd, title=window_title(hwnd), class_name=class_name(hwnd),
                      pid=pid, exe_path=process_path(pid), rect=window_rect(hwnd))


def enum_top_windows(exclude_pid: int | None = None, *, include_minimized: bool = False,
                     require_title: bool = False, resolve_exe: bool = True) -> list[WindowInfo]:
    """Visible top-level windows in Z-order (topmost first)."""
    result: list[WindowInfo] = []

    def cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd) or is_cloaked(hwnd):
                return True
            minimized = is_minimized(hwnd)
            if minimized and not include_minimized:
                return True
            cls = class_name(hwnd)
            if cls in _SKIP_CLASSES:
                return True
            pid = window_pid(hwnd)
            if exclude_pid is not None and pid == exclude_pid:
                return True
            title = window_title(hwnd)
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if ex & WS_EX_TOOLWINDOW and not title:
                return True
            if require_title and not title.strip():
                return True
            rect = window_rect(hwnd)
            if not minimized and (rect.width < 40 or rect.height < 40):
                return True
            result.append(WindowInfo(hwnd=int(hwnd), title=title, class_name=cls, pid=pid,
                                     exe_path=process_path(pid) if resolve_exe else "", rect=rect))
        except Exception:
            pass
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return result


def top_window_at(x: int, y: int, exclude_pid: int | None = None) -> WindowInfo | None:
    for w in enum_top_windows(exclude_pid, resolve_exe=False):
        if w.rect.contains(x, y):
            return WindowInfo(w.hwnd, w.title, w.class_name, w.pid, process_path(w.pid), w.rect)
    return None


def deepest_child_at(hwnd: int, x: int, y: int) -> int:
    """Deepest visible child window of ``hwnd`` containing the screen point."""
    h = hwnd
    for _ in range(32):
        pt = wt.POINT(x, y)
        user32.ScreenToClient(wt.HWND(h), ctypes.byref(pt))
        c = user32.ChildWindowFromPointEx(wt.HWND(h), pt, CWP_SKIPINVISIBLE | CWP_SKIPTRANSPARENT)
        if not c or int(c) == int(h):
            break
        h = int(c)
    return int(h)


def smallest_child_at(hwnd: int, x: int, y: int, min_size: int = 80) -> int:
    """Smallest visible descendant window (>= min_size) containing the screen point.

    Unlike ChildWindowFromPointEx this also finds WS_EX_TRANSPARENT children such
    as Chromium's render widget (Chrome, Edge, new Outlook, Electron apps).
    """
    best, best_area = 0, None

    def cb(h, _lp):
        nonlocal best, best_area
        if not user32.IsWindowVisible(h):
            return True
        r = raw_window_rect(h)
        if r.width < min_size or r.height < min_size or not r.contains(x, y):
            return True
        area = r.width * r.height
        if best_area is None or area < best_area:
            best, best_area = int(h), area
        return True

    user32.EnumChildWindows(wt.HWND(hwnd), WNDENUMPROC(cb), 0)
    return best or hwnd


def restore_window(hwnd: int) -> None:
    if is_minimized(hwnd):
        user32.ShowWindow(wt.HWND(hwnd), SW_RESTORE)
        time.sleep(0.35)


def activate_window(hwnd: int) -> bool:
    """Bring the window to the foreground (best effort)."""
    restore_window(hwnd)
    if int(user32.GetForegroundWindow() or 0) == hwnd:
        return True
    if user32.SetForegroundWindow(wt.HWND(hwnd)):
        return True
    # Foreground lock workaround: a synthetic ALT tap lets us take the foreground.
    send_key(VK_MENU)
    return bool(user32.SetForegroundWindow(wt.HWND(hwnd)))


HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]


def set_window_rect(hwnd: int, r: Rect, topmost: bool = True) -> bool:
    """Place a window at an exact physical rectangle (no activation)."""
    after = wt.HWND(HWND_TOPMOST) if topmost else wt.HWND(0)
    return bool(user32.SetWindowPos(wt.HWND(hwnd), after, r.left, r.top, r.width, r.height,
                                    SWP_NOACTIVATE | SWP_SHOWWINDOW))


def set_exclude_from_capture(hwnd: int, exclude: bool = True) -> bool:
    return bool(user32.SetWindowDisplayAffinity(wt.HWND(hwnd), WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE))


# --------------------------------------------------------------------------- input
def get_cursor_pos() -> tuple[int, int]:
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor_pos(x: int, y: int) -> None:
    user32.SetCursorPos(int(x), int(y))


def send_wheel(delta: int) -> None:
    """Send a vertical mouse-wheel event at the current cursor position.

    Positive ``delta`` scrolls up (content moves down), negative scrolls down.
    """
    inp = INPUT(type=INPUT_MOUSE)
    inp.u.mi = MOUSEINPUT(0, 0, ctypes.c_uint32(delta).value, MOUSEEVENTF_WHEEL, 0, 0)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def send_key(vk: int) -> None:
    arr = (INPUT * 2)()
    arr[0].type = INPUT_KEYBOARD
    arr[0].u.ki = KEYBDINPUT(vk, 0, 0, 0, 0)
    arr[1].type = INPUT_KEYBOARD
    arr[1].u.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, 0)
    user32.SendInput(2, arr, ctypes.sizeof(INPUT))


# --------------------------------------------------------------------------- monitors
def monitors() -> list[MonitorInfo]:
    out: list[MonitorInfo] = []

    def cb(hmon, _hdc, _rc, _lp):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            out.append(MonitorInfo(mi.szDevice, Rect._from_win(mi.rcMonitor), Rect._from_win(mi.rcWork)))
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    return out


# --------------------------------------------------------------------------- hotkeys
def register_hotkey(hwnd: int, hotkey_id: int, modifiers: int, vk: int) -> bool:
    return bool(user32.RegisterHotKey(wt.HWND(hwnd), hotkey_id, modifiers | MOD_NOREPEAT, vk))


def unregister_hotkey(hwnd: int, hotkey_id: int) -> None:
    user32.UnregisterHotKey(wt.HWND(hwnd), hotkey_id)
