import os
import glob
import winreg
import time
from dataclasses import dataclass, field
from typing import List, Optional, Callable

from utils.file_utils import format_size, safe_delete
from utils.registry import open_key_safe, enum_keys, enum_values


@dataclass
class JunkItem:
    path: str
    category: str
    description: str
    size_bytes: int = 0
    selected: bool = True

    @property
    def size_display(self) -> str:
        return format_size(self.size_bytes) if self.size_bytes > 0 else ""


@dataclass
class JunkScanResult:
    items: List[JunkItem] = field(default_factory=list)
    total_size_bytes: int = 0
    total_items: int = 0

    @property
    def total_size_display(self) -> str:
        return format_size(self.total_size_bytes)


def _get_dir_size(path: str) -> int:
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _get_file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _scan_windows_temp(progress_callback: Optional[Callable] = None) -> List[JunkItem]:
    items = []
    temp_dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Temp"),
    ]

    seen = set()
    for temp_dir in temp_dirs:
        if not temp_dir or not os.path.isdir(temp_dir) or temp_dir in seen:
            continue
        seen.add(temp_dir)
        if progress_callback:
            progress_callback(temp_dir, -1)
        size = _get_dir_size(temp_dir)
        if size > 0:
            items.append(JunkItem(
                path=temp_dir,
                category="临时文件",
                description="Windows 临时文件目录",
                size_bytes=size,
            ))

    return items


def _scan_browser_cache(progress_callback: Optional[Callable] = None) -> List[JunkItem]:
    items = []
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if not local_appdata:
        return items

    browser_cache_dirs = [
        (os.path.join(local_appdata, r"Google\Chrome\User Data\Default\Cache"),
         "浏览器缓存", "Chrome 缓存"),
        (os.path.join(local_appdata, r"Google\Chrome\User Data\Default\Code Cache"),
         "浏览器缓存", "Chrome 代码缓存"),
        (os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Cache"),
         "浏览器缓存", "Edge 缓存"),
        (os.path.join(local_appdata, r"Microsoft\Edge\User Data\Default\Code Cache"),
         "浏览器缓存", "Edge 代码缓存"),
        (os.path.join(local_appdata, r"Mozilla\Firefox\Profiles"),
         "浏览器缓存", "Firefox 缓存"),
    ]

    for cache_dir, category, desc in browser_cache_dirs:
        if os.path.isdir(cache_dir):
            if progress_callback:
                progress_callback(cache_dir, -1)
            size = _get_dir_size(cache_dir)
            if size > 0:
                items.append(JunkItem(
                    path=cache_dir,
                    category=category,
                    description=desc,
                    size_bytes=size,
                ))

    return items


def _scan_system_cache(progress_callback: Optional[Callable] = None) -> List[JunkItem]:
    items = []
    windir = os.environ.get("WINDIR", r"C:\Windows")

    prefetch_dir = os.path.join(windir, "Prefetch")
    if os.path.isdir(prefetch_dir):
        if progress_callback:
            progress_callback(prefetch_dir, -1)
        size = _get_dir_size(prefetch_dir)
        if size > 0:
            items.append(JunkItem(
                path=prefetch_dir,
                category="系统缓存",
                description="Windows 预读取文件",
                size_bytes=size,
            ))

    installer_cache = os.path.join(windir, "Installer", r"$PatchCache$")
    if os.path.isdir(installer_cache):
        if progress_callback:
            progress_callback(installer_cache, -1)
        size = _get_dir_size(installer_cache)
        if size > 0:
            items.append(JunkItem(
                path=installer_cache,
                category="系统缓存",
                description="Windows Installer 补丁缓存（删除后可能影响软件修复，请谨慎）",
                size_bytes=size,
                selected=False,
            ))

    software_dist = os.path.join(os.environ.get("LOCALAPPDATA", ""), "SoftwareDistribution")
    if not software_dist:
        software_dist = r"C:\Windows\SoftwareDistribution"
    if os.path.isdir(software_dist):
        if progress_callback:
            progress_callback(software_dist, -1)
        size = _get_dir_size(software_dist)
        if size > 0:
            items.append(JunkItem(
                path=software_dist,
                category="系统缓存",
                description="Windows Update 下载缓存",
                size_bytes=size,
                selected=False,
            ))

    return items


def _scan_recycle_bin(progress_callback: Optional[Callable] = None) -> List[JunkItem]:
    items = []
    recycle_paths = [r"C:\$Recycle.Bin"]

    for rp in recycle_paths:
        if os.path.isdir(rp):
            if progress_callback:
                progress_callback(rp, -1)
            size = _get_dir_size(rp)
            if size > 0:
                items.append(JunkItem(
                    path=rp,
                    category="回收站",
                    description="回收站文件",
                    size_bytes=size,
                ))
                break

    return items


def _scan_uninstall_residuals(progress_callback: Optional[Callable] = None) -> List[JunkItem]:
    items = []
    appdata = os.environ.get("APPDATA", "")
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    programdata = os.environ.get("PROGRAMDATA", "")

    installed_names = set()
    installed_locations = set()
    try:
        for hive_root, base_path in [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]:
            base_key = open_key_safe(hive_root, base_path)
            if base_key is None:
                continue
            for sub_name in enum_keys(base_key):
                sub_key = open_key_safe(hive_root, f"{base_path}\\{sub_name}")
                if sub_key is None:
                    continue
                try:
                    for val_name, (_, val_data) in enum_values(sub_key).items():
                        vl = val_name.lower()
                        if vl == "displayname" and val_data:
                            installed_names.add(str(val_data).strip().lower())
                        if vl in ("installdir", "installlocation") and val_data:
                            loc = str(val_data).strip().lower().rstrip("\\")
                            if loc:
                                installed_locations.add(loc)
                                installed_locations.add(os.path.basename(loc))
                except Exception:
                    pass
                winreg.CloseKey(sub_key)
            winreg.CloseKey(base_key)
    except Exception:
        pass

    KNOWN_SAFE_DIRS = {
        "microsoft", "windows", "packages", "desktop", "themes",
        "intel", "nvidia corporation", "amd", "realtek",
        "google", "mozilla", "oracle", "apple computer",
        "dropbox", "spotify", "valve", "steam", "java",
    }

    for base in [appdata, local_appdata, programdata]:
        if not base or not os.path.isdir(base):
            continue
        try:
            for entry in os.listdir(base):
                full = os.path.join(base, entry)
                if not os.path.isdir(full):
                    continue

                entry_lower = entry.lower()

                is_known_safe = False
                for safe_name in KNOWN_SAFE_DIRS:
                    if entry_lower == safe_name or entry_lower.startswith(safe_name + " "):
                        is_known_safe = True
                        break
                if is_known_safe:
                    continue

                is_installed = False
                for name in installed_names:
                    if entry_lower in name or name in entry_lower:
                        is_installed = True
                        break
                if not is_installed:
                    for loc in installed_locations:
                        if entry_lower == loc:
                            is_installed = True
                            break

                if is_installed:
                    continue

                if progress_callback:
                    progress_callback(full, -1)
                size = _get_dir_size(full)
                if size > 1024 * 1024:
                    items.append(JunkItem(
                        path=full,
                        category="卸载残留",
                        description=f"可能为已卸载软件的残留目录: {entry}",
                        size_bytes=size,
                        selected=False,
                    ))
                    if len(items) >= 50:
                        return items
        except OSError:
            continue

    return items


def _scan_log_files(progress_callback: Optional[Callable] = None) -> List[JunkItem]:
    items = []
    log_dirs = [
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("PROGRAMDATA", ""),
    ]

    seen = set()
    for base_dir in log_dirs:
        if not base_dir or not os.path.isdir(base_dir):
            continue
        try:
            for root, dirs, files in os.walk(base_dir):
                depth = root[len(base_dir):].count(os.sep)
                if depth > 2:
                    del dirs[:]
                    continue
                for f in files:
                    if f.lower().endswith((".log", ".old", ".bak")):
                        full = os.path.join(root, f)
                        if full in seen:
                            continue
                        seen.add(full)
                        if progress_callback:
                            progress_callback(full, -1)
                        size = _get_file_size(full)
                        if size > 1024:
                            items.append(JunkItem(
                                path=full,
                                category="日志文件",
                                description=f"日志/备份文件: {f}",
                                size_bytes=size,
                                selected=False,
                            ))
                if len(items) >= 100:
                    break
        except OSError:
            continue

    return items


class JunkCleaner:
    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        self._callback = progress_callback

    def _emit(self, message: str, progress: int = -1):
        if self._callback:
            self._callback(message, progress)

    def _item_progress(self, path: str, _):
        ts = time.strftime("%H:%M:%S")
        basename = os.path.basename(path) if len(path) < 60 else "..." + path[-57:]
        self._emit(f"[{ts}] 正在扫描: {basename}", -1)

    def scan(self) -> JunkScanResult:
        result = JunkScanResult()
        scanners = [
            ("临时文件", _scan_windows_temp),
            ("浏览器缓存", _scan_browser_cache),
            ("系统缓存", _scan_system_cache),
            ("回收站", _scan_recycle_bin),
            ("卸载残留", _scan_uninstall_residuals),
            ("日志文件", _scan_log_files),
        ]

        total = len(scanners)
        for i, (name, scanner) in enumerate(scanners):
            self._emit(f"正在扫描{name} ({i+1}/{total})...", int(i / total * 100))
            try:
                items = scanner(self._item_progress if name in ("卸载残留", "日志文件") else None)
                result.items.extend(items)
            except Exception:
                pass

        result.total_items = len(result.items)
        result.total_size_bytes = sum(item.size_bytes for item in result.items)
        self._emit(f"扫描完成，共发现 {result.total_items} 项，{result.total_size_display}", 100)

        return result

    def clean(self, items: List[JunkItem]) -> int:
        cleaned = 0
        for item in items:
            if not item.selected:
                continue
            if safe_delete(item.path):
                cleaned += 1
        return cleaned