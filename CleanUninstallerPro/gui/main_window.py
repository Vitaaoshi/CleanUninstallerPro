from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QStatusBar,
    QMessageBox, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QProgressBar, QApplication,
    QAbstractItemView, QFileDialog, QComboBox, QCheckBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QObject
from PyQt6.QtGui import QIcon, QFont, QColor, QAction, QCursor

import os
import sys
import subprocess
import time
import json

from core.scanner import SoftwareScanner, InstalledProgram
from core.uninstaller import Uninstaller
from core.residual_scanner import ResidualScanner, ResidualScanResult, ResidualItem
from core.install_monitor import InstallMonitor, FileChange
from core.software_classifier import (
    get_publisher_groups, set_custom_category, ALL_CATEGORIES,
    load_favorites, save_favorites,
)
from core.junk_cleaner import JunkCleaner, JunkItem, JunkScanResult
from core.background_monitor import (
    is_autostart_enabled, enable_autostart, disable_autostart,
    add_monitored_software, get_monitored_software_names,
    match_monitored_sessions_to_programs,
)
import psutil as _psutil
from utils.file_utils import format_size
from gui.residual_dialog import ResidualDialog

LIGHT_STYLE = """
QMainWindow {
    background-color: #f5f7fa;
}
QTabWidget::pane {
    border: 1px solid #e0e4e8;
    border-radius: 6px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: #e8ecf0;
    color: #5a6270;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    min-width: 90px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #2c3e50;
    font-weight: 600;
    border-bottom: 2px solid #3498db;
}
QTabBar::tab:hover:!selected {
    background: #dfe4ea;
}
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8f9fb;
    border: 1px solid #e0e4e8;
    border-radius: 6px;
    gridline-color: #eef0f3;
    selection-background-color: #e8f4fd;
    selection-color: #2c3e50;
    font-size: 13px;
}
QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #eef0f3;
}
QHeaderView::section {
    background: #f0f2f5;
    color: #5a6270;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #dce1e6;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}
QPushButton {
    background: #ffffff;
    color: #2c3e50;
    border: 1px solid #dce1e6;
    border-radius: 6px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background: #e8f4fd;
    border-color: #3498db;
    color: #2980b9;
}
QPushButton:pressed {
    background: #d0e8f7;
}
QPushButton:disabled {
    background: #f0f2f5;
    color: #b0b8c4;
    border-color: #e0e4e8;
}
QPushButton#dangerBtn {
    background: #e74c3c;
    color: #ffffff;
    border: none;
}
QPushButton#dangerBtn:hover {
    background: #c0392b;
}
QPushButton#dangerBtn:disabled {
    background: #f0b8b4;
    color: #ffffff;
}
QPushButton#primaryBtn {
    background: #3498db;
    color: #ffffff;
    border: none;
}
QPushButton#primaryBtn:hover {
    background: #2980b9;
}
QPushButton#themeBtn {
    background: #2c3e50;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#themeBtn:hover {
    background: #34495e;
}
QLineEdit {
    border: 1px solid #dce1e6;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    background: #ffffff;
}
QLineEdit:focus {
    border-color: #3498db;
}
QComboBox {
    border: 1px solid #dce1e6;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 13px;
    background: #ffffff;
    min-height: 22px;
}
QComboBox:focus {
    border-color: #3498db;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QCheckBox {
    font-size: 13px;
    color: #5a6270;
    spacing: 6px;
}
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #e8ecf0;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background: #3498db;
    border-radius: 4px;
}
QStatusBar {
    background: #ffffff;
    color: #5a6270;
    border-top: 1px solid #e0e4e8;
    font-size: 12px;
}
QMenuBar {
    background: #ffffff;
    border-bottom: 1px solid #e0e4e8;
    font-size: 13px;
}
QMenuBar::item {
    padding: 6px 14px;
}
QMenuBar::item:selected {
    background: #e8f4fd;
    color: #2980b9;
}
QMenu {
    background: #ffffff;
    border: 1px solid #e0e4e8;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 7px 28px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #e8f4fd;
    color: #2980b9;
}
QLabel#titleLabel {
    color: #2c3e50;
    font-size: 20px;
    font-weight: 700;
}
QLabel#infoLabel {
    color: #8e99a4;
    font-size: 13px;
}
QLabel#summaryLabel {
    color: #2c3e50;
    font-size: 14px;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #e74c3c;
    font-size: 14px;
    font-weight: 600;
}
QLabel#monitorLog {
    background: #1e272e;
    color: #d2dae2;
    padding: 14px;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
}
"""

DARK_STYLE = """
QMainWindow {
    background-color: #1a1a2e;
}
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    background: #16213e;
    top: -1px;
}
QTabBar::tab {
    background: #1a1a3e;
    color: #8899aa;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    min-width: 90px;
}
QTabBar::tab:selected {
    background: #16213e;
    color: #e0e8f0;
    font-weight: 600;
    border-bottom: 2px solid #3498db;
}
QTabBar::tab:hover:!selected {
    background: #1e2d50;
}
QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1a2745;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    gridline-color: #1e2d50;
    selection-background-color: #1a3458;
    selection-color: #e0e8f0;
    font-size: 13px;
    color: #c8d4e0;
}
QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #1e2d50;
}
QHeaderView::section {
    background: #1a1a3e;
    color: #8899aa;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #2a3a5a;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
}
QPushButton {
    background: #1e2d50;
    color: #c8d4e0;
    border: 1px solid #2a3a5a;
    border-radius: 6px;
    padding: 7px 18px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}
QPushButton:hover {
    background: #243860;
    border-color: #3498db;
    color: #e0e8f0;
}
QPushButton:pressed {
    background: #1a3050;
}
QPushButton:disabled {
    background: #1a1a3e;
    color: #5a6a80;
    border-color: #2a2a4a;
}
QPushButton#dangerBtn {
    background: #c0392b;
    color: #ffffff;
    border: none;
}
QPushButton#dangerBtn:hover {
    background: #e74c3c;
}
QPushButton#dangerBtn:disabled {
    background: #5a2020;
    color: #996666;
}
QPushButton#primaryBtn {
    background: #2980b9;
    color: #ffffff;
    border: none;
}
QPushButton#primaryBtn:hover {
    background: #3498db;
}
QPushButton#themeBtn {
    background: #7f8c8d;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#themeBtn:hover {
    background: #95a5a6;
}
QLineEdit {
    border: 1px solid #2a3a5a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    background: #16213e;
    color: #c8d4e0;
}
QLineEdit:focus {
    border-color: #3498db;
}
QComboBox {
    border: 1px solid #2a3a5a;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 13px;
    background: #16213e;
    color: #c8d4e0;
    min-height: 22px;
}
QComboBox:focus {
    border-color: #3498db;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #16213e;
    color: #c8d4e0;
    selection-background-color: #1a3458;
}
QCheckBox {
    font-size: 13px;
    color: #8899aa;
    spacing: 6px;
}
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #1e2d50;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background: #3498db;
    border-radius: 4px;
}
QStatusBar {
    background: #16213e;
    color: #8899aa;
    border-top: 1px solid #2a2a4a;
    font-size: 12px;
}
QMenuBar {
    background: #16213e;
    border-bottom: 1px solid #2a2a4a;
    font-size: 13px;
    color: #c8d4e0;
}
QMenuBar::item {
    padding: 6px 14px;
}
QMenuBar::item:selected {
    background: #1a3458;
    color: #e0e8f0;
}
QMenu {
    background: #16213e;
    border: 1px solid #2a3a5a;
    border-radius: 6px;
    padding: 4px;
    color: #c8d4e0;
}
QMenu::item {
    padding: 7px 28px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #1a3458;
    color: #e0e8f0;
}
QLabel#titleLabel {
    color: #e0e8f0;
    font-size: 20px;
    font-weight: 700;
}
QLabel#infoLabel {
    color: #7a8a9a;
    font-size: 13px;
}
QLabel#summaryLabel {
    color: #e0e8f0;
    font-size: 14px;
    font-weight: 600;
}
QLabel#statusLabel {
    color: #e74c3c;
    font-size: 14px;
    font-weight: 600;
}
QLabel#monitorLog {
    background: #0d1117;
    color: #c9d1d9;
    padding: 14px;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
}
"""

AGREEMENT_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "CleanUninstallerPro", "agreement_accepted.json"
)


def _is_agreement_accepted() -> bool:
    try:
        if os.path.isfile(AGREEMENT_FILE):
            with open(AGREEMENT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("accepted", False)
    except Exception:
        pass
    return False


def _save_agreement_accepted():
    try:
        os.makedirs(os.path.dirname(AGREEMENT_FILE), exist_ok=True)
        with open(AGREEMENT_FILE, "w", encoding="utf-8") as f:
            json.dump({"accepted": True, "timestamp": time.time()}, f)
    except Exception:
        pass


THEME_CONFIG_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "CleanUninstallerPro", "theme.json"
)


def _load_theme() -> str:
    try:
        if os.path.isfile(THEME_CONFIG_FILE):
            with open(THEME_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("theme", "light")
    except Exception:
        pass
    return "light"


def _save_theme(theme: str):
    try:
        os.makedirs(os.path.dirname(THEME_CONFIG_FILE), exist_ok=True)
        with open(THEME_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"theme": theme}, f)
    except Exception:
        pass


class ScanWorker(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def run(self):
        self.progress.emit("正在扫描已安装软件...")
        scanner = SoftwareScanner()
        result = scanner.scan_installed()
        self.progress.emit(f"扫描完成，发现 {len(result)} 个程序")
        self.finished.emit(result)


class UninstallWorker(QThread):
    finished = pyqtSignal(bool)
    progress = pyqtSignal(str, int)

    def __init__(self, program: InstalledProgram):
        super().__init__()
        self._program = program

    def run(self):
        uninstaller = Uninstaller(progress_callback=lambda m, p: self.progress.emit(m, p))
        result = uninstaller.uninstall(self._program)
        self.finished.emit(result)


class ForceRemoveWorker(QThread):
    finished = pyqtSignal(bool)
    progress = pyqtSignal(str, int)

    def __init__(self, program: InstalledProgram):
        super().__init__()
        self._program = program

    def run(self):
        uninstaller = Uninstaller(progress_callback=lambda m, p: self.progress.emit(m, p))
        result = uninstaller.force_remove(self._program)
        self.finished.emit(result)


class ResidualScanWorker(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(str, int)

    def __init__(self, program: InstalledProgram):
        super().__init__()
        self._program = program

    def run(self):
        scanner = ResidualScanner(progress_callback=lambda m, p: self.progress.emit(m, p))
        result = scanner.scan(self._program)
        self.finished.emit(result)


class JunkScanWorker(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(str, int)

    def run(self):
        cleaner = JunkCleaner(progress_callback=lambda m, p: self.progress.emit(m, p))
        result = cleaner.scan()
        self.finished.emit(result)


class JunkCleanWorker(QThread):
    finished = pyqtSignal(int, int)

    def __init__(self, items: list[JunkItem]):
        super().__init__()
        self._items = items

    def run(self):
        cleaner = JunkCleaner()
        selected = [i for i in self._items if i.selected]
        cleaned = cleaner.clean(selected)
        self.finished.emit(cleaned, len(selected))


class _MonitorSignals(QObject):
    file_change = pyqtSignal(object)
    proc_detected = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CleanUninstaller Pro v1.0")
        self.resize(1200, 760)
        self.setMinimumSize(860, 520)

        self._current_theme = _load_theme()
        self._apply_theme()

        self._programs: list[InstalledProgram] = []
        self._current_scan_result: ResidualScanResult = None
        self._junk_result: JunkScanResult = None
        self._monitor = InstallMonitor(callback=self._on_monitor_event)
        self._selected_installer_path: str = ""
        self._hide_system = True
        self._current_category = "全部"
        self._current_publisher = "全部"
        self._operation_running = False
        self._favorites: set = load_favorites()

        self._monitor_signals = _MonitorSignals()
        self._monitor_signals.file_change.connect(self._on_monitor_change)
        self._monitor_signals.proc_detected.connect(self._on_monitor_proc_detected)

        self._setup_ui()
        self._setup_menu()

        if not _is_agreement_accepted():
            QTimer.singleShot(100, self._show_agreement)
        else:
            QTimer.singleShot(300, self._refresh_list)

    def _show_agreement(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("使用须知 & 免责声明")
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        dialog.setText(
            "<h3 style='color:#2c3e50'>【使用须知 & 免责声明】</h3>"
            "<p style='color:#5a6270;line-height:1.6;font-size:12px'>"
            "本工具为免费开源系统监控软件，仅用于个人技术学习与合法场景使用。<br><br>"
            "本程序会读取系统应用安装、卸载相关数据，使用即代表您已知悉并同意以下条款：<br><br>"
            "<b>1.</b> 您自愿使用本软件，因操作不当、系统环境、安全软件拦截造成的任何损失，"
            "均由使用者自行负责。<br><br>"
            "<b>2.</b> 禁止将本软件用于非法用途，违反法律法规的行为责任自负。<br><br>"
            "<b>3.</b> 本软件开源免费，原作者不对使用过程中产生的各类问题承担任何法律责任。<br><br>"
            "</p>"
            "<p style='color:#e74c3c;font-size:12px;font-weight:600'>"
            "点击「是」表示我已阅读并同意以上条款</p>"
        )
        result = dialog.exec()
        if result == QMessageBox.StandardButton.Yes:
            _save_agreement_accepted()
            QTimer.singleShot(300, self._refresh_list)
        else:
            self.close()

    def _apply_theme(self):
        if self._current_theme == "dark":
            self.setStyleSheet(DARK_STYLE)
        else:
            self.setStyleSheet(LIGHT_STYLE)

    def _toggle_theme(self):
        self._current_theme = "dark" if self._current_theme == "light" else "light"
        _save_theme(self._current_theme)
        self._apply_theme()
        theme_label = "暗色" if self._current_theme == "dark" else "亮色"
        self._theme_btn.setText("  " + ("☀" if self._current_theme == "dark" else "🌙") + "  切换主题")
        self._status.showMessage(f"已切换到{theme_label}主题")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        title_bar = QHBoxLayout()
        title = QLabel("CleanUninstaller Pro")
        title.setObjectName("titleLabel")
        title_bar.addWidget(title)
        title_bar.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("  搜索软件...")
        self._search_input.setFixedWidth(280)
        self._search_input.setFixedHeight(34)
        self._search_input.textChanged.connect(self._on_search)
        title_bar.addWidget(self._search_input)

        self._theme_btn = QPushButton(
            "  ☀  切换主题" if self._current_theme == "dark" else "  🌙  切换主题"
        )
        self._theme_btn.setObjectName("themeBtn")
        self._theme_btn.setFixedHeight(34)
        self._theme_btn.clicked.connect(self._toggle_theme)
        title_bar.addWidget(self._theme_btn)

        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setObjectName("primaryBtn")
        refresh_btn.setFixedHeight(34)
        refresh_btn.clicked.connect(self._refresh_list)
        title_bar.addWidget(refresh_btn)

        layout.addLayout(title_bar)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._setup_software_tab()
        self._setup_junk_cleaner_tab()
        self._setup_monitor_tab()

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("就绪")

    def _setup_software_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 10, 6, 6)
        layout.setSpacing(8)

        filter_row1 = QHBoxLayout()
        filter_row1.setSpacing(12)

        filter_row1.addWidget(QLabel("分类:"))
        self._category_combo = QComboBox()
        self._category_combo.setFixedWidth(140)
        self._category_combo.addItem("全部")
        self._category_combo.currentTextChanged.connect(self._on_category_changed)
        filter_row1.addWidget(self._category_combo)

        filter_row1.addWidget(QLabel("发布者:"))
        self._publisher_combo = QComboBox()
        self._publisher_combo.setFixedWidth(220)
        self._publisher_combo.addItem("全部")
        self._publisher_combo.currentTextChanged.connect(self._on_publisher_changed)
        filter_row1.addWidget(self._publisher_combo)

        filter_row1.addWidget(QLabel("日期:"))
        self._date_combo = QComboBox()
        self._date_combo.setFixedWidth(120)
        self._date_combo.addItems(["全部", "最近7天", "最近30天", "最近半年", "半年以上"])
        self._date_combo.currentTextChanged.connect(self._on_date_changed)
        filter_row1.addWidget(self._date_combo)

        filter_row1.addWidget(QLabel("大小:"))
        self._size_combo = QComboBox()
        self._size_combo.setFixedWidth(130)
        self._size_combo.addItems(["全部", "> 1 GB", "100 MB - 1 GB", "10 MB - 100 MB", "< 10 MB"])
        self._size_combo.currentTextChanged.connect(self._on_size_changed)
        filter_row1.addWidget(self._size_combo)

        filter_row1.addStretch()
        layout.addLayout(filter_row1)

        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(12)

        self._hide_system_cb = QCheckBox("隐藏系统软件")
        self._hide_system_cb.setChecked(True)
        self._hide_system_cb.stateChanged.connect(self._on_hide_system_changed)
        filter_row2.addWidget(self._hide_system_cb)

        self._only_favorites_cb = QCheckBox("仅显示收藏")
        self._only_favorites_cb.stateChanged.connect(self._on_only_favorites_changed)
        filter_row2.addWidget(self._only_favorites_cb)

        self._show_unused_cb = QCheckBox("标记闲置软件(≥半年)")
        self._show_unused_cb.stateChanged.connect(self._on_show_unused_changed)
        filter_row2.addWidget(self._show_unused_cb)

        self._only_monitored_cb = QCheckBox("仅显示已监控")
        self._only_monitored_cb.stateChanged.connect(self._on_only_monitored_changed)
        filter_row2.addWidget(self._only_monitored_cb)

        filter_row2.addStretch()
        layout.addLayout(filter_row2)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._uninstall_btn = QPushButton("卸载选中")
        self._uninstall_btn.setFixedHeight(34)
        self._uninstall_btn.clicked.connect(self._uninstall_selected)
        self._uninstall_btn.setEnabled(False)
        toolbar.addWidget(self._uninstall_btn)

        self._batch_uninstall_btn = QPushButton("批量卸载")
        self._batch_uninstall_btn.setObjectName("dangerBtn")
        self._batch_uninstall_btn.setFixedHeight(34)
        self._batch_uninstall_btn.clicked.connect(self._batch_uninstall)
        self._batch_uninstall_btn.setEnabled(False)
        toolbar.addWidget(self._batch_uninstall_btn)

        self._force_remove_btn = QPushButton("强制移除")
        self._force_remove_btn.setObjectName("dangerBtn")
        self._force_remove_btn.setFixedHeight(34)
        self._force_remove_btn.clicked.connect(self._force_remove_selected)
        self._force_remove_btn.setEnabled(False)
        toolbar.addWidget(self._force_remove_btn)

        self._scan_residual_btn = QPushButton("扫描残留")
        self._scan_residual_btn.setFixedHeight(34)
        self._scan_residual_btn.clicked.connect(self._scan_residual)
        self._scan_residual_btn.setEnabled(False)
        toolbar.addWidget(self._scan_residual_btn)

        self._view_publisher_btn = QPushButton("查看同发布者")
        self._view_publisher_btn.setFixedHeight(34)
        self._view_publisher_btn.clicked.connect(self._view_same_publisher)
        self._view_publisher_btn.setEnabled(False)
        toolbar.addWidget(self._view_publisher_btn)

        toolbar.addStretch()

        self._selection_count_label = QLabel("")
        self._selection_count_label.setStyleSheet("font-size: 13px; color: #3498db; font-weight: 600;")
        toolbar.addWidget(self._selection_count_label)

        layout.addLayout(toolbar)

        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels(
            ["收藏", "软件名称", "分类", "版本", "发布者", "安装路径", "大小", "安装日期", "状态"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_table_context_menu)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(0, 48)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)

        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_table_double_click)

        layout.addWidget(self._table)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setFixedHeight(6)
        layout.addWidget(self._progress_bar)

        self._tabs.addTab(tab, "软件列表")

    def _setup_junk_cleaner_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 10, 6, 6)
        layout.setSpacing(8)

        info = QLabel(
            "扫描并清理系统临时文件、浏览器缓存、系统缓存、回收站、卸载残留和日志文件，释放磁盘空间。"
        )
        info.setObjectName("infoLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._junk_scan_btn = QPushButton("扫描垃圾")
        self._junk_scan_btn.setObjectName("primaryBtn")
        self._junk_scan_btn.setFixedHeight(36)
        self._junk_scan_btn.clicked.connect(self._junk_scan)
        btn_layout.addWidget(self._junk_scan_btn)

        self._junk_clean_btn = QPushButton("清理选中项")
        self._junk_clean_btn.setObjectName("dangerBtn")
        self._junk_clean_btn.setFixedHeight(36)
        self._junk_clean_btn.clicked.connect(self._junk_clean)
        self._junk_clean_btn.setEnabled(False)
        btn_layout.addWidget(self._junk_clean_btn)

        self._junk_select_all_btn = QPushButton("全选")
        self._junk_select_all_btn.setFixedHeight(36)
        self._junk_select_all_btn.clicked.connect(self._junk_select_all)
        self._junk_select_all_btn.setEnabled(False)
        btn_layout.addWidget(self._junk_select_all_btn)

        self._junk_deselect_all_btn = QPushButton("取消全选")
        self._junk_deselect_all_btn.setFixedHeight(36)
        self._junk_deselect_all_btn.clicked.connect(self._junk_deselect_all)
        self._junk_deselect_all_btn.setEnabled(False)
        btn_layout.addWidget(self._junk_deselect_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._junk_progress_label = QLabel("")
        self._junk_progress_label.setObjectName("infoLabel")
        self._junk_progress_label.setWordWrap(True)
        layout.addWidget(self._junk_progress_label)

        self._junk_summary_label = QLabel("")
        self._junk_summary_label.setObjectName("summaryLabel")
        layout.addWidget(self._junk_summary_label)

        self._junk_table = QTableWidget()
        self._junk_table.setColumnCount(5)
        self._junk_table.setHorizontalHeaderLabels(
            ["选择", "类别", "描述", "路径", "大小"]
        )
        self._junk_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._junk_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._junk_table.setAlternatingRowColors(True)
        self._junk_table.verticalHeader().setVisible(False)

        header = self._junk_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._junk_table)
        self._tabs.addTab(tab, "垃圾清理")

    def _setup_monitor_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(6, 10, 6, 6)
        layout.setSpacing(8)

        info = QLabel(
            "选择要监控的安装程序，在安装过程中实时追踪文件系统变化。\n"
            "1. 选择安装程序(.exe/.msi) → 2. 开始监控 → 3. 运行安装程序 → 4. 停止监控查看摘要"
        )
        info.setObjectName("infoLabel")
        info.setWordWrap(True)
        layout.addWidget(info)

        installer_layout = QHBoxLayout()
        installer_layout.setSpacing(10)
        self._select_installer_btn = QPushButton("选择安装程序")
        self._select_installer_btn.setObjectName("primaryBtn")
        self._select_installer_btn.setFixedHeight(34)
        self._select_installer_btn.clicked.connect(self._select_installer)
        installer_layout.addWidget(self._select_installer_btn)

        self._installer_info_label = QLabel("未选择安装程序")
        self._installer_info_label.setStyleSheet(
            "font-size: 13px; padding: 6px 12px; color: #e74c3c; "
            "border: 1px dashed #dce1e6; border-radius: 6px;"
        )
        installer_layout.addWidget(self._installer_info_label, 1)
        layout.addLayout(installer_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._monitor_start_btn = QPushButton("开始监控")
        self._monitor_start_btn.setObjectName("primaryBtn")
        self._monitor_start_btn.setFixedHeight(36)
        self._monitor_start_btn.clicked.connect(self._start_monitoring)
        btn_layout.addWidget(self._monitor_start_btn)

        self._monitor_stop_btn = QPushButton("停止监控")
        self._monitor_stop_btn.setObjectName("dangerBtn")
        self._monitor_stop_btn.setFixedHeight(36)
        self._monitor_stop_btn.clicked.connect(self._stop_monitoring)
        self._monitor_stop_btn.setEnabled(False)
        btn_layout.addWidget(self._monitor_stop_btn)

        self._monitor_clear_btn = QPushButton("清空日志")
        self._monitor_clear_btn.setFixedHeight(36)
        self._monitor_clear_btn.clicked.connect(self._clear_monitor_log)
        self._monitor_clear_btn.setEnabled(False)
        btn_layout.addWidget(self._monitor_clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        status_layout = QHBoxLayout()
        status_layout.setSpacing(16)

        self._monitor_status = QLabel("状态: 未启动")
        self._monitor_status.setObjectName("statusLabel")
        status_layout.addWidget(self._monitor_status)

        self._monitor_proc_label = QLabel("")
        self._monitor_proc_label.setStyleSheet("font-size: 13px; color: #8e44ad; font-weight: 600;")
        status_layout.addWidget(self._monitor_proc_label)

        self._monitor_counter = QLabel("已检测: 0 项变更")
        self._monitor_counter.setStyleSheet("font-size: 13px; color: #3498db; font-weight: 600;")
        status_layout.addWidget(self._monitor_counter)

        self._monitor_timer = QLabel("运行时间: 00:00:00")
        self._monitor_timer.setStyleSheet("font-size: 13px; color: #27ae60;")
        status_layout.addWidget(self._monitor_timer)

        status_layout.addStretch()
        layout.addLayout(status_layout)

        self._monitor_table = QTableWidget()
        self._monitor_table.setColumnCount(4)
        self._monitor_table.setHorizontalHeaderLabels(["时间", "类型", "来源", "路径"])
        self._monitor_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._monitor_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._monitor_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._monitor_table.setAlternatingRowColors(True)
        self._monitor_table.verticalHeader().setVisible(False)
        self._monitor_table.setSortingEnabled(False)
        self._monitor_table.setMinimumHeight(200)

        header = self._monitor_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._monitor_table)

        self._monitor_log = QLabel("")
        self._monitor_log.setObjectName("monitorLog")
        self._monitor_log.setWordWrap(True)
        self._monitor_log.setMinimumHeight(100)
        layout.addWidget(self._monitor_log)

        self._monitor_time_counter = 0
        self._monitor_timer_interval = QTimer()
        self._monitor_timer_interval.timeout.connect(self._update_monitor_timer)
        self._monitor_max_log_lines = 1000
        self._monitor_log_lines = []

        bg_layout = QHBoxLayout()
        bg_layout.setSpacing(12)
        bg_layout.addWidget(QLabel("后台监控"))
        self._bg_status_label = QLabel("")
        self._bg_status_label.setStyleSheet("font-size: 13px;")
        bg_layout.addWidget(self._bg_status_label)

        self._bg_auto_start_cb = QCheckBox("开机自动启动后台监控")
        self._bg_auto_start_cb.setChecked(is_autostart_enabled())
        self._bg_auto_start_cb.stateChanged.connect(self._on_auto_start_changed)
        bg_layout.addWidget(self._bg_auto_start_cb)

        self._bg_start_btn = QPushButton("启动后台监控")
        self._bg_start_btn.setFixedHeight(34)
        self._bg_start_btn.clicked.connect(self._start_bg_service)
        bg_layout.addWidget(self._bg_start_btn)

        self._bg_stop_btn = QPushButton("停止后台监控")
        self._bg_stop_btn.setFixedHeight(34)
        self._bg_stop_btn.clicked.connect(self._stop_bg_service)
        self._bg_stop_btn.setEnabled(False)
        bg_layout.addWidget(self._bg_stop_btn)

        bg_layout.addStretch()
        layout.addLayout(bg_layout)

        self._bg_process = None

        self._tabs.addTab(tab, "安装监控")

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        refresh_action = QAction("刷新软件列表", self)
        refresh_action.triggered.connect(self._refresh_list)
        file_menu.addAction(refresh_action)
        file_menu.addSeparator()
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        tools_menu = menubar.addMenu("工具")
        junk_action = QAction("垃圾清理", self)
        junk_action.triggered.connect(lambda: self._tabs.setCurrentIndex(1))
        tools_menu.addAction(junk_action)

        view_menu = menubar.addMenu("视图")
        theme_action = QAction("切换暗色/亮色主题", self)
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)

        help_menu = menubar.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _on_table_context_menu(self, pos):
        program = self._get_selected_program()
        if not program:
            return

        menu = QMenu(self)

        open_folder_action = QAction("打开文件位置", self)
        open_folder_action.triggered.connect(self._open_file_location)
        menu.addAction(open_folder_action)

        toggle_fav_action = QAction(
            "取消收藏" if program.is_favorite else "添加收藏", self
        )
        toggle_fav_action.triggered.connect(self._toggle_favorite)
        menu.addAction(toggle_fav_action)

        menu.addSeparator()

        change_cat_menu = menu.addMenu("修改分类")

        for cat in ALL_CATEGORIES:
            action = QAction(cat, self)
            action.triggered.connect(lambda checked, c=cat: self._change_category(c))
            if cat == program.category:
                font = action.font()
                font.setBold(True)
                action.setFont(font)
            change_cat_menu.addAction(action)

        menu.addSeparator()

        uninstall_action = menu.addAction("卸载")
        uninstall_action.triggered.connect(self._uninstall_selected)
        force_action = menu.addAction("强制移除")
        force_action.triggered.connect(self._force_remove_selected)
        residual_action = menu.addAction("扫描残留")
        residual_action.triggered.connect(self._scan_residual)

        menu.exec(QCursor.pos())

    def _open_file_location(self):
        program = self._get_selected_program()
        if not program:
            return
        target = program.install_path
        if not target or not os.path.exists(target):
            target = os.path.dirname(target) if target else ""
        if not target or not os.path.exists(target):
            QMessageBox.information(self, "提示", "未找到该软件的安装目录")
            return
        try:
            os.startfile(target)
        except Exception:
            subprocess.Popen(["explorer", target])

    def _toggle_favorite(self):
        program = self._get_selected_program()
        if not program:
            return
        program.is_favorite = not program.is_favorite
        if program.is_favorite:
            self._favorites.add(program.name)
        else:
            self._favorites.discard(program.name)
        save_favorites(self._favorites)
        self._populate_table()
        status_text = "已收藏" if program.is_favorite else "已取消收藏"
        self._status.showMessage(f"「{program.name}」{status_text}")

    def _change_category(self, new_category: str):
        program = self._get_selected_program()
        if not program:
            return
        if new_category == program.category:
            return

        set_custom_category(program.name, new_category)
        program.category = new_category

        self._update_category_combo()
        self._populate_table()
        self._status.showMessage(f"已将「{program.name}」分类修改为: {new_category}")

    def _refresh_list(self):
        self._status.showMessage("正在扫描已安装软件...")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)

        self._scan_worker = ScanWorker()
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.progress.connect(lambda m: self._status.showMessage(m))
        self._scan_worker.start()

    def _on_scan_finished(self, programs):
        self._programs = programs
        self._favorites = load_favorites()
        for p in self._programs:
            p.is_favorite = p.name in self._favorites
        self._progress_bar.setVisible(False)
        self._status.showMessage(f"共发现 {len(programs)} 个已安装程序")
        self._update_category_combo()
        self._update_publisher_combo()
        self._populate_table()

    def _update_category_combo(self):
        self._category_combo.blockSignals(True)
        current = self._category_combo.currentText()
        self._category_combo.clear()
        self._category_combo.addItem("全部")
        categories = sorted(set(p.category for p in self._programs if p.category))
        for cat in categories:
            count = sum(1 for p in self._programs if p.category == cat)
            self._category_combo.addItem(f"{cat} ({count})")
        idx = self._category_combo.findText(current)
        if idx >= 0:
            self._category_combo.setCurrentIndex(idx)
        self._category_combo.blockSignals(False)

    def _update_publisher_combo(self):
        self._publisher_combo.blockSignals(True)
        current = self._publisher_combo.currentText()
        self._publisher_combo.clear()
        self._publisher_combo.addItem("全部")
        groups = get_publisher_groups(self._programs)
        for pub, progs in groups.items():
            self._publisher_combo.addItem(f"{pub} ({len(progs)})")
        idx = self._publisher_combo.findText(current)
        if idx >= 0:
            self._publisher_combo.setCurrentIndex(idx)
        self._publisher_combo.blockSignals(False)

    def _get_category_filter(self) -> str:
        text = self._category_combo.currentText()
        if text == "全部":
            return "全部"
        return text.split(" (")[0]

    def _get_publisher_filter(self) -> str:
        text = self._publisher_combo.currentText()
        if text == "全部":
            return "全部"
        return text.split(" (")[0]

    def _get_date_filter(self) -> str:
        return self._date_combo.currentText()

    def _get_size_filter(self) -> str:
        return self._size_combo.currentText()

    def _populate_table(self, filter_text: str = ""):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        category = self._get_category_filter()
        publisher = self._get_publisher_filter()
        date_filter = self._get_date_filter()
        size_filter = self._get_size_filter()
        only_fav = self._only_favorites_cb.isChecked()
        show_unused = self._show_unused_cb.isChecked()
        only_monitored = self._only_monitored_cb.isChecked()

        filtered = self._programs
        if self._hide_system:
            filtered = [p for p in filtered if not p.is_system]
        if category != "全部":
            filtered = [p for p in filtered if p.category == category]
        if publisher != "全部":
            filtered = [p for p in filtered if p.publisher == publisher]
        if only_fav:
            filtered = [p for p in filtered if p.is_favorite]
        if only_monitored:
            filtered = [p for p in filtered if p.is_monitored]
        if filter_text:
            ft = filter_text.lower()
            filtered = [
                p for p in filtered
                if ft in p.name.lower() or ft in (p.publisher or "").lower()
            ]

        if date_filter == "最近7天":
            filtered = [p for p in filtered if p.last_modified_days <= 7]
        elif date_filter == "最近30天":
            filtered = [p for p in filtered if p.last_modified_days <= 30]
        elif date_filter == "最近半年":
            filtered = [p for p in filtered if p.last_modified_days <= 180]
        elif date_filter == "半年以上":
            filtered = [p for p in filtered if p.last_modified_days > 180]

        if size_filter == "> 1 GB":
            filtered = [p for p in filtered if p.size_bytes > 1024 * 1024 * 1024]
        elif size_filter == "100 MB - 1 GB":
            filtered = [p for p in filtered if 100 * 1024 * 1024 < p.size_bytes <= 1024 * 1024 * 1024]
        elif size_filter == "10 MB - 100 MB":
            filtered = [p for p in filtered if 10 * 1024 * 1024 < p.size_bytes <= 100 * 1024 * 1024]
        elif size_filter == "< 10 MB":
            filtered = [p for p in filtered if 0 < p.size_bytes <= 10 * 1024 * 1024]

        self._filtered_programs = filtered
        self._table.setRowCount(len(filtered))

        cat_colors = {
            "系统工具": "#95a5a6", "安全软件": "#e74c3c", "浏览器": "#3498db",
            "开发工具": "#2ecc71", "办公软件": "#f39c12", "图形设计": "#9b59b6",
            "影音娱乐": "#1abc9c", "网络工具": "#e67e22", "压缩解压": "#34495e",
            "通讯社交": "#2980b9", "其他": "#bdc3c7",
        }

        for row, prog in enumerate(filtered):
            fav_item = QTableWidgetItem("★" if prog.is_favorite else "☆")
            fav_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if prog.is_favorite:
                fav_item.setForeground(QColor("#f39c12"))
                fav_item.setToolTip("点击切换收藏状态")
            self._table.setItem(row, 0, fav_item)

            name_item = QTableWidgetItem(prog.name)
            if show_unused and prog.is_unused:
                name_item.setForeground(QColor("#e67e22"))
                name_item.setToolTip("该软件超过半年未使用")
            self._table.setItem(row, 1, name_item)

            cat_item = QTableWidgetItem(prog.category)
            cat_item.setForeground(QColor(cat_colors.get(prog.category, "#5a6270")))
            self._table.setItem(row, 2, cat_item)

            self._table.setItem(row, 3, QTableWidgetItem(prog.version))
            self._table.setItem(row, 4, QTableWidgetItem(prog.publisher))
            self._table.setItem(row, 5, QTableWidgetItem(prog.install_path))
            self._table.setItem(row, 6, QTableWidgetItem(prog.size_display))
            self._table.setItem(row, 7, QTableWidgetItem(prog.install_date))

            status_text = ""
            if prog.is_monitored:
                status_text = "已监控"
            if prog.is_favorite:
                status_text = ("收藏" if not status_text else status_text + "·收藏")
            if show_unused and prog.is_unused:
                status_text = ("闲置" if not status_text else status_text + "·闲置")
            status_item = QTableWidgetItem(status_text)
            if "闲置" in status_text:
                status_item.setForeground(QColor("#e67e22"))
            if "已监控" in status_text:
                status_item.setForeground(QColor("#27ae60"))
            if "收藏" in status_text:
                status_item.setForeground(QColor("#f39c12"))
            self._table.setItem(row, 8, status_item)

            self._table.setRowHeight(row, 30)

        self._table.setSortingEnabled(True)

        total = len(self._programs)
        hidden = sum(1 for p in self._programs if p.is_system) if self._hide_system else 0
        self._status.showMessage(
            f"显示 {len(filtered)} 个程序 (共 {total} 个"
            + (f", 已隐藏 {hidden} 个系统软件)" if hidden > 0 else ")")
        )

    def _on_search(self, text: str):
        self._populate_table(filter_text=text)

    def _on_category_changed(self, text: str):
        self._populate_table()

    def _on_publisher_changed(self, text: str):
        self._populate_table()

    def _on_date_changed(self, text: str):
        self._populate_table()

    def _on_size_changed(self, text: str):
        self._populate_table()

    def _on_only_favorites_changed(self, state):
        self._populate_table()

    def _on_show_unused_changed(self, state):
        self._populate_table()

    def _on_only_monitored_changed(self, state):
        self._populate_table()

    def _on_hide_system_changed(self, state):
        self._hide_system = state == Qt.CheckState.Checked.value
        self._populate_table()

    def _view_same_publisher(self):
        program = self._get_selected_program()
        if not program or not program.publisher:
            return
        publisher = program.publisher
        for i in range(self._publisher_combo.count()):
            if self._publisher_combo.itemText(i).startswith(publisher + " ("):
                self._publisher_combo.setCurrentIndex(i)
                return

    def _on_selection_changed(self):
        selected_rows = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())
        count = len(selected_rows)
        has_selection = count > 0

        self._uninstall_btn.setEnabled(has_selection)
        self._force_remove_btn.setEnabled(has_selection)
        self._scan_residual_btn.setEnabled(has_selection)
        self._batch_uninstall_btn.setEnabled(count > 1)

        selected = self._get_selected_program()
        self._view_publisher_btn.setEnabled(selected is not None and bool(selected.publisher))

        if count > 0:
            self._selection_count_label.setText(f"已选 {count} 项")
        else:
            self._selection_count_label.setText("")

    def _on_table_double_click(self, index):
        if self._operation_running:
            return
        col = index.column()
        if col == 0:
            name_item = self._table.item(index.row(), 1)
            if not name_item:
                return
            name = name_item.text()
            filtered = getattr(self, '_filtered_programs', self._programs)
            for p in filtered:
                if p.name == name:
                    p.is_favorite = not p.is_favorite
                    if p.is_favorite:
                        self._favorites.add(p.name)
                    else:
                        self._favorites.discard(p.name)
                    save_favorites(self._favorites)
                    self._populate_table()
                    status_text = "已收藏" if p.is_favorite else "已取消收藏"
                    self._status.showMessage(f"「{p.name}」{status_text}")
                    return
        elif col == 2:
            cat_item = self._table.item(index.row(), 2)
            if cat_item:
                cat_name = cat_item.text()
                for i in range(self._category_combo.count()):
                    if self._category_combo.itemText(i).startswith(cat_name + " ("):
                        self._category_combo.setCurrentIndex(i)
                        return
        elif col == 4:
            pub_item = self._table.item(index.row(), 4)
            if pub_item:
                pub_name = pub_item.text()
                for i in range(self._publisher_combo.count()):
                    if self._publisher_combo.itemText(i).startswith(pub_name + " ("):
                        self._publisher_combo.setCurrentIndex(i)
                        return
        elif col == 5:
            name_item = self._table.item(index.row(), 1)
            if not name_item:
                return
            name = name_item.text()
            filtered = getattr(self, '_filtered_programs', self._programs)
            for p in filtered:
                if p.name == name:
                    if p.install_path and os.path.exists(p.install_path):
                        try:
                            os.startfile(p.install_path)
                        except Exception:
                            subprocess.Popen(["explorer", p.install_path])
                    return
        else:
            self._scan_residual()

    def _get_selected_program(self) -> InstalledProgram | None:
        rows = set()
        for item in self._table.selectedItems():
            rows.add(item.row())
        if not rows:
            return None
        row = list(rows)[0]
        name_item = self._table.item(row, 1)
        if not name_item:
            return None
        name = name_item.text()
        filtered = getattr(self, '_filtered_programs', self._programs)
        for p in filtered:
            if p.name == name:
                return p
        return None

    def _get_selected_programs(self) -> list[InstalledProgram]:
        rows = set()
        for item in self._table.selectedItems():
            rows.add(item.row())
        if not rows:
            return []
        result = []
        filtered = getattr(self, '_filtered_programs', self._programs)
        for row in rows:
            name_item = self._table.item(row, 1)
            if not name_item:
                continue
            name = name_item.text()
            for p in filtered:
                if p.name == name:
                    result.append(p)
                    break
        return result

    def _batch_uninstall(self):
        if self._operation_running:
            return
        programs = self._get_selected_programs()
        if len(programs) < 2:
            QMessageBox.information(self, "提示", "请至少选择2个软件进行批量卸载")
            return

        names = "\n".join(f"  • {p.name}" for p in programs[:10])
        suffix = f"\n  ... 等共 {len(programs)} 个" if len(programs) > 10 else ""

        reply = QMessageBox.question(
            self, "确认批量卸载",
            f"将依次卸载以下 {len(programs)} 个软件：\n\n{names}{suffix}\n\n确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._batch_queue = list(programs)
        self._batch_results = []
        self._operation_running = True
        self._status.showMessage(f"批量卸载: 共 {len(self._batch_queue)} 个")
        self._process_batch_next()

    def _process_batch_next(self):
        if not self._batch_queue:
            self._operation_running = False
            success = sum(1 for r in self._batch_results if r)
            fail = len(self._batch_results) - success
            QMessageBox.information(
                self, "批量卸载完成",
                f"成功: {success} 个\n失败: {fail} 个"
            )
            QTimer.singleShot(1000, self._refresh_list)
            return

        program = self._batch_queue.pop(0)
        self._status.showMessage(f"批量卸载 ({len(self._batch_queue) + 1}/{len(self._batch_results) + len(self._batch_queue) + 1}): {program.name}")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._batch_wait_dialog = None

        self._uninstall_worker = UninstallWorker(program)
        self._uninstall_worker.finished.connect(self._on_batch_uninstall_finished)
        self._uninstall_worker.progress.connect(lambda m, p: self._status.showMessage(m))
        self._uninstall_worker.start()

    def _on_batch_uninstall_finished(self, success: bool):
        self._batch_results.append(success)
        self._progress_bar.setVisible(False)
        QTimer.singleShot(800, self._process_batch_next)

    def _uninstall_selected(self):
        if self._operation_running:
            return
        program = self._get_selected_program()
        if not program:
            return
        reply = QMessageBox.question(
            self, "确认卸载",
            f"确定要卸载「{program.name}」吗？\n\n发布者: {program.publisher}\n版本: {program.version}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._operation_running = True
        self._status.showMessage(f"正在卸载: {program.name}")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._uninstall_worker = UninstallWorker(program)
        self._uninstall_worker.finished.connect(self._on_uninstall_finished)
        self._uninstall_worker.progress.connect(lambda m, p: self._status.showMessage(m))
        self._uninstall_worker.start()

    def _on_uninstall_finished(self, success: bool):
        self._operation_running = False
        self._progress_bar.setVisible(False)
        if success:
            self._status.showMessage("卸载完成")
            QTimer.singleShot(1000, self._refresh_list)
            QTimer.singleShot(1500, self._prompt_residual_scan)
        else:
            self._status.showMessage("卸载可能未完全成功")
            QTimer.singleShot(500, self._prompt_residual_scan)

    def _prompt_residual_scan(self):
        reply = QMessageBox.question(
            self, "残留扫描", "是否立即扫描残留文件和注册表项？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._scan_residual()

    def _force_remove_selected(self):
        if self._operation_running:
            return
        program = self._get_selected_program()
        if not program:
            return
        reply = QMessageBox.warning(
            self, "强制移除警告",
            f"强制移除「{program.name}」将直接删除其注册表项和安装目录。\n\n此操作不可逆，确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._operation_running = True
        self._status.showMessage(f"正在强制移除: {program.name}")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._force_remove_worker = ForceRemoveWorker(program)
        self._force_remove_worker.finished.connect(self._on_force_remove_finished)
        self._force_remove_worker.progress.connect(lambda m, p: self._status.showMessage(m))
        self._force_remove_worker.start()

    def _on_force_remove_finished(self, success: bool):
        self._operation_running = False
        self._progress_bar.setVisible(False)
        if success:
            self._status.showMessage("强制移除完成")
            QTimer.singleShot(1000, self._refresh_list)
        else:
            self._status.showMessage("强制移除失败")

    def _scan_residual(self):
        if self._operation_running:
            return
        program = self._get_selected_program()
        if not program:
            QMessageBox.information(self, "提示", "请先从列表中选择一个软件")
            return
        self._operation_running = True
        self._status.showMessage(f"正在扫描残留: {program.name}")
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 100)
        self._residual_worker = ResidualScanWorker(program)
        self._residual_worker.finished.connect(self._on_residual_result)
        self._residual_worker.progress.connect(self._on_residual_progress)
        self._residual_worker.start()

    def _on_residual_progress(self, message: str, progress: int):
        self._status.showMessage(message)
        if progress >= 0:
            self._progress_bar.setValue(progress)

    def _on_residual_result(self, result: ResidualScanResult):
        self._operation_running = False
        self._progress_bar.setVisible(False)
        self._current_scan_result = result
        self._show_residual_dialog(result)
        if result.total_items > 0:
            QTimer.singleShot(500, self._refresh_list)

    def _show_residual_dialog(self, result: ResidualScanResult):
        self._status.showMessage(
            f"残留扫描完成: {result.total_items} 项, {result.total_size_display}"
        )
        dialog = ResidualDialog(result, self)
        dialog.exec()

    def _junk_scan(self):
        if self._operation_running:
            QMessageBox.information(self, "提示", "当前有其他操作正在进行，请稍后再试")
            return
        self._junk_scan_btn.setEnabled(False)
        self._junk_clean_btn.setEnabled(False)
        self._junk_select_all_btn.setEnabled(False)
        self._junk_deselect_all_btn.setEnabled(False)
        self._junk_summary_label.setText("")
        self._junk_progress_label.setText("正在扫描...")
        self._status.showMessage("正在扫描系统垃圾...")
        self._junk_scan_worker = JunkScanWorker()
        self._junk_scan_worker.finished.connect(self._on_junk_scan_finished)
        self._junk_scan_worker.progress.connect(self._on_junk_scan_progress)
        self._junk_scan_worker.start()

    def _on_junk_scan_progress(self, message: str, progress: int):
        self._junk_progress_label.setText(message)

    def _on_junk_scan_finished(self, result: JunkScanResult):
        self._junk_result = result
        self._junk_scan_btn.setEnabled(True)
        self._junk_clean_btn.setEnabled(len(result.items) > 0)
        self._junk_select_all_btn.setEnabled(len(result.items) > 0)
        self._junk_deselect_all_btn.setEnabled(len(result.items) > 0)
        self._junk_progress_label.setText("")
        self._junk_summary_label.setText(
            f"扫描完成: 共 {result.total_items} 项, 可释放 {result.total_size_display} 空间"
        )
        self._status.showMessage(
            f"垃圾扫描完成: {result.total_items} 项, {result.total_size_display}"
        )
        self._populate_junk_table(result)

    def _populate_junk_table(self, result: JunkScanResult):
        self._junk_table.setRowCount(len(result.items))
        cat_colors = {
            "临时文件": "#e74c3c", "浏览器缓存": "#3498db", "系统缓存": "#f39c12",
            "回收站": "#95a5a6", "卸载残留": "#9b59b6", "日志文件": "#7f8c8d",
        }
        for row, item in enumerate(result.items):
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox = QCheckBox()
            checkbox.setChecked(item.selected)
            checkbox.stateChanged.connect(
                lambda state, i=item: setattr(i, "selected", state == Qt.CheckState.Checked.value)
            )
            cb_layout.addWidget(checkbox)
            self._junk_table.setCellWidget(row, 0, cb_widget)

            cat_item = QTableWidgetItem(item.category)
            cat_item.setForeground(QColor(cat_colors.get(item.category, "#2c3e50")))
            self._junk_table.setItem(row, 1, cat_item)
            self._junk_table.setItem(row, 2, QTableWidgetItem(item.description))
            self._junk_table.setItem(row, 3, QTableWidgetItem(item.path))
            self._junk_table.setItem(row, 4, QTableWidgetItem(item.size_display))
            self._junk_table.setRowHeight(row, 28)

    def _junk_clean(self):
        if not self._junk_result:
            return
        selected = [i for i in self._junk_result.items if i.selected]
        if not selected:
            QMessageBox.information(self, "提示", "未选择任何需要清理的项目")
            return
        total_size = sum(i.size_bytes for i in selected)
        reply = QMessageBox.warning(
            self, "确认清理",
            f"将清理 {len(selected)} 项垃圾文件，释放约 {format_size(total_size)} 空间。\n\n确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._junk_clean_btn.setEnabled(False)
        self._junk_clean_btn.setText("清理中...")
        self._junk_clean_worker = JunkCleanWorker(self._junk_result.items)
        self._junk_clean_worker.finished.connect(self._on_junk_clean_finished)
        self._junk_clean_worker.start()

    def _on_junk_clean_finished(self, cleaned: int, total: int):
        self._junk_clean_btn.setText("清理选中项")
        self._junk_clean_btn.setEnabled(True)
        QMessageBox.information(self, "清理完成", f"成功清理 {cleaned} / {total} 项")
        self._junk_scan()

    def _junk_select_all(self):
        if not self._junk_result:
            return
        for row in range(self._junk_table.rowCount()):
            widget = self._junk_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
        for item in self._junk_result.items:
            item.selected = True

    def _junk_deselect_all(self):
        if not self._junk_result:
            return
        for row in range(self._junk_table.rowCount()):
            widget = self._junk_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        for item in self._junk_result.items:
            item.selected = False

    def _start_monitoring(self):
        self._monitor_start_btn.setEnabled(False)
        self._monitor_stop_btn.setEnabled(True)
        self._monitor_clear_btn.setEnabled(True)
        self._select_installer_btn.setEnabled(False)
        self._monitor_status.setText("状态: 正在监控...")
        self._monitor_proc_label.setText("")
        self._monitor_counter.setText("已检测: 0 项变更")
        self._monitor_timer.setText("运行时间: 00:00:00")
        self._monitor_time_counter = 0
        self._monitor_table.setRowCount(0)
        self._monitor_log_lines.clear()
        self._monitor_log.setText("")
        if self._selected_installer_path:
            self._monitor.set_installer(self._selected_installer_path)
        self._monitor.set_change_callback(self._monitor_signals.file_change.emit)
        self._monitor.set_proc_callback(self._monitor_signals.proc_detected.emit)
        self._monitor.start_monitoring()
        self._monitor_timer_interval.start(1000)

    def _stop_monitoring(self):
        self._monitor_timer_interval.stop()
        session = self._monitor.stop_monitoring()
        self._monitor_start_btn.setEnabled(True)
        self._monitor_stop_btn.setEnabled(False)
        self._monitor_proc_label.setText("")
        self._select_installer_btn.setEnabled(True)
        self._monitor_status.setText("状态: 已停止")
        self._monitor_status.setStyleSheet("font-size: 14px; color: #27ae60; font-weight: 600;")
        summary = self._monitor.get_summary()
        lines = ["=== 安装监控摘要 ===", ""]
        lines.extend(summary)
        lines.append("")
        lines.append(f"总计文件变更: {len(session.file_changes)} 项")
        self._monitor_log.setText("\n".join(lines))

        for program in self._programs:
            if program.install_path:
                install_path_lower = program.install_path.lower().rstrip("\\")
                for change in session.file_changes:
                    change_path = change.path.lower()
                    if change_path.startswith(install_path_lower + "\\"):
                        add_monitored_software(program.name)
                        program.is_monitored = True
                        break
        QTimer.singleShot(500, self._populate_table)

    def _select_installer(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择安装程序", "", "安装程序 (*.exe *.msi);;所有文件 (*.*)"
        )
        if file_path:
            self._selected_installer_path = file_path
            basename = os.path.basename(file_path)
            self._installer_info_label.setText(f"[选中] {basename}  ({file_path})")
            self._installer_info_label.setStyleSheet(
                "font-size: 13px; padding: 6px 12px; color: #27ae60; "
                "border: 1px solid #27ae60; border-radius: 6px;"
            )
            self._status.showMessage(f"已选择安装程序: {basename}")

    def _on_monitor_event(self, message: str):
        pass

    def _on_monitor_proc_detected(self, message: str):
        self._monitor_proc_label.setText(message)

    def _on_monitor_change(self, change: FileChange):
        row_count = self._monitor_table.rowCount()
        if row_count >= self._monitor_max_log_lines:
            self._monitor_table.removeRow(row_count - 1)
        self._monitor_table.insertRow(0)

        self._monitor_table.setItem(0, 0, QTableWidgetItem(change.format_time()))

        type_item = QTableWidgetItem(change.change_type.upper())
        type_colors = {"created": "#27ae60", "modified": "#f39c12", "deleted": "#e74c3c",
                       "moved_from": "#e67e22", "moved_to": "#2ecc71"}
        type_item.setForeground(QColor(type_colors.get(change.change_type, "#5a6270")))
        self._monitor_table.setItem(0, 1, type_item)

        source_item = QTableWidgetItem(change.source)
        source_item.setForeground(QColor("#8e44ad"))
        self._monitor_table.setItem(0, 2, source_item)

        self._monitor_table.setItem(0, 3, QTableWidgetItem(change.path))
        self._monitor_table.setRowHeight(0, 26)

        source_info = f" [{change.source}]" if change.source and change.source != "未知安装程序" else ""
        self._monitor_log_lines.insert(
            0, f"[{change.format_time()}] {change.change_type.upper()}{source_info}: {change.path}"
        )
        if len(self._monitor_log_lines) > 50:
            self._monitor_log_lines.pop()
        self._monitor_log.setText("\n".join(self._monitor_log_lines))
        self._monitor_counter.setText(f"已检测: {len(self._monitor.session.file_changes)} 项变更")

    def _update_monitor_timer(self):
        self._monitor_time_counter += 1
        h = self._monitor_time_counter // 3600
        m = (self._monitor_time_counter % 3600) // 60
        s = self._monitor_time_counter % 60
        self._monitor_timer.setText(f"运行时间: {h:02d}:{m:02d}:{s:02d}")

    def _clear_monitor_log(self):
        self._monitor_table.setRowCount(0)
        self._monitor_log_lines.clear()
        self._monitor_log.setText("")

    def _on_auto_start_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        if enabled:
            success = enable_autostart()
            if success:
                self._status.showMessage("已启用开机自启")
            else:
                self._bg_auto_start_cb.blockSignals(True)
                self._bg_auto_start_cb.setChecked(False)
                self._bg_auto_start_cb.blockSignals(False)
                QMessageBox.warning(self, "权限不足", "无法写入注册表，请以管理员权限运行")
        else:
            disable_autostart()
            self._status.showMessage("已禁用开机自启")

    def _start_bg_service(self):
        try:
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                bg_exe = os.path.join(exe_dir, "CleanUninstallerPro_Bg.exe")
                if not os.path.isfile(bg_exe):
                    bg_exe = sys.executable.replace("CleanUninstallerPro.exe", "CleanUninstallerPro_Bg.exe")
                if os.path.isfile(bg_exe):
                    self._bg_process = subprocess.Popen(
                        [bg_exe],
                        creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
                    )
                else:
                    QMessageBox.warning(self, "启动失败", "未找到后台监控程序 CleanUninstallerPro_Bg.exe")
                    return
            else:
                bg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bg_service.py")
                if os.path.isfile(bg_path):
                    self._bg_process = subprocess.Popen(
                        [sys.executable, bg_path],
                        creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
                    )
                else:
                    QMessageBox.warning(self, "启动失败", f"未找到后台服务脚本: {bg_path}")
                    return
            self._bg_start_btn.setEnabled(False)
            self._bg_stop_btn.setEnabled(True)
            self._bg_status_label.setText("● 运行中")
            self._bg_status_label.setStyleSheet("font-size: 13px; color: #27ae60; font-weight: 600;")
            self._status.showMessage("后台监控已启动，托盘区域可见图标")
        except Exception as e:
            QMessageBox.warning(self, "启动失败", f"无法启动后台监控: {e}")

    def _stop_bg_service(self):
        if self._bg_process is not None:
            try:
                self._bg_process.terminate()
                self._bg_process.wait(timeout=5)
            except Exception:
                try:
                    self._bg_process.kill()
                except Exception:
                    pass
            self._bg_process = None
        else:
            try:
                for proc in _psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        exe = (proc.info['exe'] or "").lower()
                        if exe.endswith("cleanuninstallerpro_bg.exe"):
                            proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            except Exception:
                pass
        self._bg_start_btn.setEnabled(True)
        self._bg_stop_btn.setEnabled(False)
        self._bg_status_label.setText("○ 未运行")
        self._bg_status_label.setStyleSheet("font-size: 13px; color: #95a5a6;")
        self._status.showMessage("后台监控已停止")

    def _show_about(self):
        QMessageBox.about(
            self, "关于 CleanUninstaller Pro",
            "<h2 style='color:#2c3e50;margin:0 0 8px 0'>CleanUninstaller Pro v1.0</h2>"
            "<p style='color:#7f8c8d;margin:0 0 12px 0;font-size:12px'>"
            "Copyright &copy; 2026 白衣傲世 &nbsp;|&nbsp; "
            "<a href='https://github.com/Vitaaoshi' style='color:#3498db'>GitHub: Vitaaoshi</a></p>"
            "<hr style='border:none;border-top:1px solid #e0e4e8;margin:0 0 10px 0'>"
            "<h4 style='color:#2c3e50;margin:0 0 4px 0'>核心功能</h4>"
            "<ul style='color:#5a6270;margin:2px 0 8px 0;padding-left:18px;font-size:12px'>"
            "<li>软件安装过程实时监控，追踪文件系统变化</li>"
            "<li>后台静默监控 + 开机自启，无需手动操作</li>"
            "<li>彻底扫描注册表与磁盘中的卸载残留</li>"
            "<li>智能分类管理（自动分类 + 手动修改）</li>"
            "<li>暗色/亮色主题切换</li>"
            "<li>收藏标记 + 闲置软件检测</li>"
            "<li>垃圾文件/浏览器缓存/系统缓存一键清理</li>"
            "<li>批量卸载 + 强制移除</li>"
            "</ul>"
            "<hr style='border:none;border-top:1px solid #e0e4e8;margin:0 0 8px 0'>"
            "<p style='color:#e74c3c;margin:0 0 6px 0;font-size:11px;font-weight:600'>"
            "免责声明</p>"
            "<p style='color:#7f8c8d;margin:0 0 8px 0;font-size:11px;line-height:1.5'>"
            "本软件为个人免费开源工具，仅供学习、技术研究使用。<br>"
            "使用本软件所产生的一切系统变动、数据风险、软硬件故障等，均由使用者自行承担，"
            "作者不承担任何法律及经济责任。<br>"
            "请勿用于非法用途，禁止恶意篡改、捆绑发布。</p>"
            "<p style='color:#7f8c8d;margin:0;font-size:11px;line-height:1.5'>"
            "本软件基于 <b>MIT License</b> 开源发布，允许自由使用、修改和分发。</p>"
        )