"""Entry point: logging, single instance, QApplication."""
from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from . import APP_NAME, __version__
from .i18n import set_language, tr
from .settings import Settings, app_data_dir

SERVER_NAME = "ScrollCapture-single-instance"
log = logging.getLogger("scrollcapture")


def _setup_logging() -> str:
    path = app_data_dir() / "scrollcapture.log"
    handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if sys.stderr is not None:
        root.addHandler(logging.StreamHandler())
    return str(path)


def _install_excepthook(log_path: str) -> None:
    def hook(exc_type, exc, tb):
        log.error("unhandled exception:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        try:
            QMessageBox.critical(None, APP_NAME, tr("err.unexpected", err=exc, log=log_path))
        except Exception:
            pass

    sys.excepthook = hook


def _notify_running_instance() -> bool:
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True
    return False


def main() -> int:
    log_path = _setup_logging()
    log.info("%s %s starting", APP_NAME, __version__)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)

    settings = Settings.load()
    set_language(settings.language)
    _install_excepthook(log_path)

    if _notify_running_instance():
        log.info("another instance is running; asked it to show")
        return 0
    server = QLocalServer()
    QLocalServer.removeServer(SERVER_NAME)
    server.listen(SERVER_NAME)

    # Imported late so the language is set before any UI strings are built.
    from .controller import Controller
    from .ui import theme
    from .ui.resources import app_icon

    app.setWindowIcon(app_icon())
    theme.install(app)
    ctl = Controller(settings)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), ctl.bring_to_front()))

    def on_main_closed():
        app.quit()

    ctl.main.destroyed.connect(on_main_closed)
    ctl.main.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    ctl.show()
    code = app.exec()
    settings.save()
    log.info("exit %s", code)
    return code


if __name__ == "__main__":
    sys.exit(main())
