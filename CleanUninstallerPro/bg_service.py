import os
import sys
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox,
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from core.background_monitor import (
    BackgroundMonitor, get_monitored_software_names, add_monitored_software,
    MONITORED_SESSIONS_FILE,
)


class _BgSignals(QObject):
    installer_detected = pyqtSignal(str, str)
    installer_finished = pyqtSignal(str, int)
    file_change = pyqtSignal(str, str)


class BgServiceApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)

        self._signals = _BgSignals()
        self._signals.installer_detected.connect(self._on_installer_detected)
        self._signals.installer_finished.connect(self._on_installer_finished)

        self._monitor = BackgroundMonitor(
            on_installer_detected=self._signals.installer_detected.emit,
            on_installer_finished=self._signals.installer_finished.emit,
        )

        self._tray = QSystemTrayIcon()
        self._tray.setToolTip("CleanUninstaller Pro - 后台安装监控")
        self._setup_tray_icon()

        self._menu = QMenu()
        self._setup_menu()

        self._tray.setContextMenu(self._menu)
        self._tray.show()

        self._monitor.start()

        tray_msg = "CleanUninstaller Pro\n后台安装监控已启动\n检测到安装程序时将自动记录"
        self._tray.showMessage("后台监控", tray_msg, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _setup_tray_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.isfile(icon_path):
            self._tray.setIcon(QIcon(icon_path))
        else:
            self._tray.setIcon(self.style().standardIcon(
                self.style().StandardPixmap.SP_ComputerIcon
            ))

    def _setup_menu(self):
        status_action = QAction("状态: 监控运行中  ✓")
        status_action.setEnabled(False)
        self._menu.addAction(status_action)

        self._menu.addSeparator()

        open_action = QAction("打开 CleanUninstaller Pro", self)
        open_action.triggered.connect(self._open_main_app)
        self._menu.addAction(open_action)

        self._menu.addSeparator()

        exit_action = QAction("退出后台监控", self)
        exit_action.triggered.connect(self._quit_service)
        self._menu.addAction(exit_action)

    def _open_main_app(self):
        try:
            if getattr(sys, 'frozen', False):
                main_exe = sys.executable.replace("_bg", "")
                if os.path.isfile(main_exe):
                    subprocess.Popen([main_exe])
                else:
                    subprocess.Popen([sys.executable])
            else:
                main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
                subprocess.Popen([sys.executable, main_py])
        except Exception:
            pass

    def _on_installer_detected(self, name: str, exe: str):
        display = f"{name}"
        if exe:
            display = f"{name}\n{exe}"
        self._tray.showMessage(
            "检测到安装程序",
            display,
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def _on_installer_finished(self, name: str, change_count: int):
        self._tray.showMessage(
            "安装已完成",
            f"{name} 已退出\n记录 {change_count} 项文件变更",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def _quit_service(self):
        self._monitor.stop()
        self._tray.hide()
        self.quit()


def main():
    app = BgServiceApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()