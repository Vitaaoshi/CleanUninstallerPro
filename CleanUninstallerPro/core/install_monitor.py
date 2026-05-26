import os
import time
import threading
import psutil
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


INSTALLER_PROCESS_NAMES = {
    "setup.exe", "install.exe", "installer.exe",
    "msiexec.exe", "update.exe",
    "patch.exe", "msedgewebview2setup.exe",
    "setup64.exe", "installer64.exe",
}

IGNORE_TOP_DIRS = {
    "$recycle.bin", "system volume information",
    "windows", "winnt",
}

IGNORE_DIR_NAMES = {
    "temp", "tmp", "logs", "__pycache__",
}

IGNORE_EXTENSIONS = {".tmp", ".temp", ".log", ".cache", ".lock", ".bak"}


@dataclass
class FileChange:
    path: str
    change_type: str
    timestamp: float = 0.0
    source: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def format_time(self):
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp))


@dataclass
class RegistryChange:
    path: str
    change_type: str
    timestamp: float = 0.0
    source: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class MonitorSession:
    start_time: float = 0.0
    file_changes: List[FileChange] = field(default_factory=list)
    registry_changes: List[RegistryChange] = field(default_factory=list)
    is_recording: bool = False
    installer_path: str = ""
    installer_name: str = ""
    detected_installer_pids: Set[int] = field(default_factory=set)
    detected_installer_names: Set[str] = field(default_factory=set)
    installer_active: bool = False
    _active_lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self):
        if self.start_time == 0.0:
            self.start_time = time.time()

    def clear(self):
        self.file_changes.clear()
        self.registry_changes.clear()
        self.start_time = time.time()
        self.detected_installer_pids.clear()
        self.detected_installer_names.clear()
        with self._active_lock:
            self.installer_active = False

    @property
    def elapsed_time(self):
        return time.time() - self.start_time

    @property
    def source_label(self) -> str:
        if self.detected_installer_names:
            return ", ".join(sorted(self.detected_installer_names))
        if self.installer_name:
            return self.installer_name
        return "未知安装程序"

    def set_installer_active(self, active: bool):
        with self._active_lock:
            self.installer_active = active

    def is_installer_active(self) -> bool:
        with self._active_lock:
            return self.installer_active


def _get_monitor_directories():
    dirs = []
    candidates = [
        os.environ.get("PROGRAMFILES", "C:\\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
        os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData")),
        os.path.join(os.environ.get("LOCALAPPDATA", "")),
        os.path.join(os.environ.get("APPDATA", "")),
        os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
    ]
    for d in candidates:
        if d and os.path.isdir(d):
            dirs.append(d)
    return dirs


class InstallFileHandler(FileSystemEventHandler):

    def __init__(self, session: MonitorSession, callback: Optional[Callable[[FileChange], None]] = None):
        super().__init__()
        self._session = session
        self._callback = callback
        self._last_notify_time = 0
        self._notify_interval = 0.05
        self._monitor_roots = [d.lower().rstrip("\\") for d in _get_monitor_directories()]

    def _should_ignore(self, path: str) -> bool:
        lower_path = path.lower()
        parts = lower_path.replace("\\", "/").split("/")

        if parts and parts[0] in IGNORE_TOP_DIRS:
            return True

        basename = os.path.basename(path).lower()
        _, ext = os.path.splitext(basename)
        if ext in IGNORE_EXTENSIONS:
            return True
        if basename.endswith("~"):
            return True

        return False

    def _notify(self, change: FileChange):
        if self._callback:
            now = time.time()
            if now - self._last_notify_time >= self._notify_interval:
                self._callback(change)
                self._last_notify_time = now

    def _get_source(self) -> str:
        if self._session.is_installer_active():
            return self._session.source_label
        return "系统后台"

    def _create_change(self, path: str, change_type: str):
        if not self._session.is_recording:
            return
        if self._should_ignore(path):
            return
        change = FileChange(
            path=path,
            change_type=change_type,
            source=self._get_source(),
        )
        self._session.file_changes.append(change)
        self._notify(change)

    def on_created(self, event: FileSystemEvent):
        self._create_change(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent):
        self._create_change(event.src_path, "modified")

    def on_deleted(self, event: FileSystemEvent):
        self._create_change(event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent):
        self._create_change(event.src_path, "moved_from")
        self._create_change(event.dest_path, "moved_to")


def _scan_installer_processes(session: MonitorSession):
    detected_new = False
    current_pids: Set[int] = set()
    current_names: Set[str] = set()

    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                info = proc.info
                name = (info['name'] or "").lower()
                pid = info['pid']

                is_installer = False
                if name in INSTALLER_PROCESS_NAMES:
                    is_installer = True
                if session.installer_path:
                    exe = (info['exe'] or "").lower()
                    installer_lower = session.installer_path.lower()
                    if exe == installer_lower or exe.endswith("\\" + session.installer_name.lower()):
                        is_installer = True

                if is_installer:
                    current_pids.add(pid)
                    current_names.add(info['name'])
                    if pid not in session.detected_installer_pids:
                        session.detected_installer_pids.add(pid)
                        session.detected_installer_names.add(info['name'])
                        detected_new = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass

    session.set_installer_active(len(current_pids) > 0)
    return detected_new


class InstallMonitor:
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self._callback = callback
        self._session = MonitorSession()
        self._observer: Optional[Observer] = None
        self._running = False
        self._change_callback: Optional[Callable[[FileChange], None]] = None
        self._proc_callback: Optional[Callable[[str], None]] = None
        self._proc_thread: Optional[threading.Thread] = None
        self._proc_stop_event = threading.Event()

    def set_change_callback(self, callback: Callable[[FileChange], None]):
        self._change_callback = callback

    def set_proc_callback(self, callback: Callable[[str], None]):
        self._proc_callback = callback

    def set_installer(self, installer_path: str):
        self._session.installer_path = os.path.abspath(installer_path)
        self._session.installer_name = os.path.basename(installer_path)

    def _notify(self, message: str):
        if self._callback:
            self._callback(message)

    def _notify_proc(self, message: str):
        if self._proc_callback:
            self._proc_callback(message)

    def _process_monitor_loop(self):
        last_scan_time = 0
        scan_interval = 2.0
        was_active = False

        while not self._proc_stop_event.is_set():
            if self._session.is_recording:
                now = time.time()
                if now - last_scan_time >= scan_interval:
                    detected = _scan_installer_processes(self._session)
                    is_active = self._session.is_installer_active()

                    if detected:
                        self._notify_proc(f"检测到安装程序进程: {self._session.source_label}")

                    if is_active and not was_active:
                        self._notify_proc(f"安装程序已启动: {self._session.source_label}")
                    elif not is_active and was_active:
                        self._notify_proc("安装程序已退出，变更将标记为系统后台")
                    was_active = is_active

                    last_scan_time = now
            time.sleep(1)

    def start_monitoring(self):
        if self._running:
            return

        self._session.clear()
        self._session.is_recording = True

        self._observer = Observer()
        handler = InstallFileHandler(self._session, self._change_callback)
        monitor_dirs = _get_monitor_directories()
        for watch_dir in monitor_dirs:
            try:
                self._observer.schedule(handler, watch_dir, recursive=True)
            except Exception:
                pass

        self._observer.start()

        self._proc_stop_event.clear()
        self._proc_thread = threading.Thread(target=self._process_monitor_loop, daemon=True)
        self._proc_thread.start()

        self._running = True
        source_info = ""
        if self._session.installer_path:
            source_info = f" (目标: {self._session.installer_name})"
        self._notify(f"安装监控已启动{source_info}")

    def stop_monitoring(self) -> MonitorSession:
        self._session.is_recording = False
        self._session.set_installer_active(False)

        self._proc_stop_event.set()
        if self._proc_thread and self._proc_thread.is_alive():
            self._proc_thread.join(timeout=3)

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

        self._running = False
        self._notify(f"安装监控已停止，共记录 {len(self._session.file_changes)} 项文件变更")
        return self._session

    @property
    def is_monitoring(self) -> bool:
        return self._running

    @property
    def session(self) -> MonitorSession:
        return self._session

    def get_summary(self) -> List[str]:
        if not self._session.file_changes:
            return ["无变更记录"]

        installer_changes: List[FileChange] = []
        system_changes: List[FileChange] = []

        for change in self._session.file_changes:
            if change.source == "系统后台":
                system_changes.append(change)
            else:
                installer_changes.append(change)

        new_dirs: Set[str] = set()
        modified_files: Set[str] = set()
        deleted_files: Set[str] = set()

        for change in installer_changes:
            if change.change_type == "created":
                if os.path.isdir(change.path):
                    new_dirs.add(change.path)
                else:
                    modified_files.add(change.path)
            elif change.change_type == "modified":
                modified_files.add(change.path)
            elif change.change_type == "deleted":
                deleted_files.add(change.path)
            elif change.change_type == "moved_to":
                modified_files.add(change.path)

        summary = []
        if self._session.source_label != "未知安装程序":
            summary.append(f"安装程序来源: {self._session.source_label}")
        summary.append(f"安装程序相关变更: {len(installer_changes)} 项")
        summary.append(f"系统后台变更: {len(system_changes)} 项 (仅供参考)")

        if new_dirs:
            summary.append(f"新建目录: {len(new_dirs)} 个")
            for d in sorted(new_dirs)[:10]:
                summary.append(f"  + {d}")
            if len(new_dirs) > 10:
                summary.append(f"  ... 还有 {len(new_dirs) - 10} 个")
        if modified_files:
            summary.append(f"新增/修改文件: {len(modified_files)} 个")
            for f in sorted(modified_files)[:10]:
                summary.append(f"  * {f}")
            if len(modified_files) > 10:
                summary.append(f"  ... 还有 {len(modified_files) - 10} 个")
        if deleted_files:
            summary.append(f"被删除的文件: {len(deleted_files)} 个")

        return summary if summary else ["监控期间未检测到显著变更"]