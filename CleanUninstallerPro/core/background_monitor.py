import os
import sys
import time
import json
import threading
import winreg
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Set, Dict

import psutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

INSTALLER_PROCESS_NAMES = {
    "setup.exe", "install.exe", "installer.exe",
    "msiexec.exe", "update.exe",
    "patch.exe", "msedgewebview2setup.exe",
    "setup64.exe", "installer64.exe",
}

IGNORE_TOP_DIRS = {"$recycle.bin", "system volume information", "windows", "winnt"}
IGNORE_EXTENSIONS = {".tmp", ".temp", ".log", ".cache", ".lock", ".bak"}

MONITORED_SESSIONS_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "CleanUninstallerPro", "monitored_sessions.json"
)
MONITORED_SOFTWARE_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "CleanUninstallerPro", "monitored_software.json"
)


@dataclass
class BgFileChange:
    path: str
    change_type: str
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class BgMonitorSession:
    session_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    installer_exe: str = ""
    installer_name: str = ""
    installer_pid: int = 0
    file_changes: List[dict] = field(default_factory=list)
    detection_count: int = 0

    def __post_init__(self):
        if self.session_id == "":
            self.session_id = time.strftime("%Y%m%d_%H%M%S")
        if self.start_time == 0.0:
            self.start_time = time.time()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "installer_exe": self.installer_exe,
            "installer_name": self.installer_name,
            "installer_pid": self.installer_pid,
            "file_changes": self.file_changes,
            "detection_count": self.detection_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BgMonitorSession":
        s = cls()
        s.session_id = data.get("session_id", "")
        s.start_time = data.get("start_time", 0.0)
        s.end_time = data.get("end_time", 0.0)
        s.installer_exe = data.get("installer_exe", "")
        s.installer_name = data.get("installer_name", "")
        s.installer_pid = data.get("installer_pid", 0)
        s.file_changes = data.get("file_changes", [])
        s.detection_count = data.get("detection_count", 0)
        return s


def _get_monitor_dirs() -> List[str]:
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


class BgFileHandler(FileSystemEventHandler):
    def __init__(self, session: BgMonitorSession, callback: Optional[Callable] = None):
        super().__init__()
        self._session = session
        self._callback = callback

    def _should_ignore(self, path: str) -> bool:
        lower = path.lower()
        parts = lower.replace("\\", "/").split("/")
        if parts and parts[0] in IGNORE_TOP_DIRS:
            return True
        basename = os.path.basename(path).lower()
        _, ext = os.path.splitext(basename)
        if ext in IGNORE_EXTENSIONS:
            return True
        if basename.endswith("~"):
            return True
        return False

    def _add_change(self, path: str, change_type: str):
        if self._should_ignore(path):
            return
        change = {"path": path, "type": change_type, "time": time.time()}
        self._session.file_changes.append(change)
        self._session.detection_count += 1
        if self._callback:
            self._callback(path, change_type)

    def on_created(self, event: FileSystemEvent):
        self._add_change(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent):
        self._add_change(event.src_path, "modified")

    def on_deleted(self, event: FileSystemEvent):
        self._add_change(event.src_path, "deleted")

    def on_moved(self, event: FileSystemEvent):
        self._add_change(event.src_path, "moved_from")
        self._add_change(event.dest_path, "moved_to")


class BackgroundMonitor:
    def __init__(self, on_installer_detected: Optional[Callable[[str, str], None]] = None,
                 on_installer_finished: Optional[Callable[[str, int], None]] = None,
                 on_file_change: Optional[Callable[[str, str], None]] = None):
        self._on_installer_detected = on_installer_detected
        self._on_installer_finished = on_installer_finished
        self._on_file_change = on_file_change
        self._running = False
        self._active_sessions: Dict[int, tuple] = {}
        self._poll_interval = 3.0
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def active_session_count(self) -> int:
        return len(self._active_sessions)

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        for pid, (session, observer) in list(self._active_sessions.items()):
            try:
                observer.stop()
                observer.join(timeout=2)
            except Exception:
                pass
            session.end_time = time.time()
            self._save_session(session)
        self._active_sessions.clear()

    def _monitor_loop(self):
        known_active_pids: Set[int] = set()
        while not self._stop_event.is_set():
            if not self._running:
                break
            try:
                current_installer_pids: Set[int] = set()
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        name = (proc.info['name'] or "").lower()
                        pid = proc.info['pid']
                        if name in INSTALLER_PROCESS_NAMES:
                            current_installer_pids.add(pid)
                            if pid not in known_active_pids and pid not in self._active_sessions:
                                self._on_installer_start(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                for pid in list(self._active_sessions.keys()):
                    if pid not in current_installer_pids:
                        self._on_installer_stop(pid)

                known_active_pids = current_installer_pids
            except Exception:
                pass

            time.sleep(self._poll_interval)

    def _on_installer_start(self, proc_info: dict):
        pid = proc_info['pid']
        exe = proc_info['exe'] or ""
        name = proc_info['name'] or ""

        session = BgMonitorSession()
        session.installer_exe = exe
        session.installer_name = name
        session.installer_pid = pid

        observer = Observer()
        handler = BgFileHandler(session, callback=self._on_file_change)
        for watch_dir in _get_monitor_dirs():
            try:
                observer.schedule(handler, watch_dir, recursive=True)
            except Exception:
                pass
        observer.start()

        self._active_sessions[pid] = (session, observer)

        if self._on_installer_detected:
            self._on_installer_detected(name, exe)

    def _on_installer_stop(self, pid: int):
        entry = self._active_sessions.pop(pid, None)
        if entry is None:
            return

        session, observer = entry
        try:
            observer.stop()
            observer.join(timeout=3)
        except Exception:
            pass

        session.end_time = time.time()
        self._save_session(session)

        if self._on_installer_finished:
            self._on_installer_finished(session.installer_name, session.detection_count)

    def _save_session(self, session: BgMonitorSession):
        sessions = self._load_sessions()
        sessions.append(session.to_dict())
        if len(sessions) > 100:
            sessions = sessions[-100:]
        try:
            os.makedirs(os.path.dirname(MONITORED_SESSIONS_FILE), exist_ok=True)
            with open(MONITORED_SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_sessions(self) -> List[dict]:
        try:
            if os.path.isfile(MONITORED_SESSIONS_FILE):
                with open(MONITORED_SESSIONS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def get_sessions(self) -> List[BgMonitorSession]:
        return [BgMonitorSession.from_dict(d) for d in self._load_sessions()]


def _load_sessions_raw() -> List[dict]:
    try:
        if os.path.isfile(MONITORED_SESSIONS_FILE):
            with open(MONITORED_SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def get_monitored_software_names() -> Set[str]:
    try:
        if os.path.isfile(MONITORED_SOFTWARE_FILE):
            with open(MONITORED_SOFTWARE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def add_monitored_software(name: str):
    names = get_monitored_software_names()
    names.add(name)
    _save_monitored_software(names)


def _save_monitored_software(names: Set[str]):
    try:
        os.makedirs(os.path.dirname(MONITORED_SOFTWARE_FILE), exist_ok=True)
        with open(MONITORED_SOFTWARE_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(names)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = "CleanUninstallerProBg"


def _get_autostart_command() -> str:
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}" --bg'
    else:
        return f'"{sys.executable}" "{os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bg_service.py"))}"'


def is_autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0,
                             winreg.KEY_SET_VALUE | winreg.KEY_READ)
        winreg.SetValueEx(key, AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, _get_autostart_command())
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable_autostart():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0,
                             winreg.KEY_SET_VALUE | winreg.KEY_READ)
        try:
            winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def match_monitored_sessions_to_programs(installed_programs: list) -> Set[str]:
    matched: Set[str] = set()
    sessions = _load_sessions_raw()
    if not sessions:
        return matched

    monitored_paths: Set[str] = set()
    for session in sessions:
        for change in session.get("file_changes", []):
            path = (change.get("path") or "").lower()
            if path:
                monitored_paths.add(path)

    for prog in installed_programs:
        name_lower = (prog.name or "").lower()
        install_path = (prog.install_path or "").lower().rstrip("\\")

        if not install_path:
            continue

        for mp in monitored_paths:
            if mp.startswith(install_path + "\\") or mp.startswith(install_path + "/"):
                matched.add(prog.name)
                break

        if prog.name in get_monitored_software_names():
            matched.add(prog.name)

    return matched