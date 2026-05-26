import os
import time
import winreg
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Set

from core.scanner import InstalledProgram, SoftwareScanner
from utils.registry import open_key_safe, enum_keys, enum_values, parse_reg_path
from utils.file_utils import (
    find_directories_containing, find_files_containing,
    safe_delete, format_size, get_size, RESIDUAL_COMMON_DIRS,
)


@dataclass
class ResidualItem:
    path: str
    item_type: str
    description: str = ""
    size_bytes: int = 0
    selected: bool = True

    @property
    def size_display(self) -> str:
        return format_size(self.size_bytes) if self.size_bytes > 0 else ""


@dataclass
class ResidualScanResult:
    program_name: str
    registry_items: List[ResidualItem] = field(default_factory=list)
    file_items: List[ResidualItem] = field(default_factory=list)
    total_items: int = 0
    total_size_bytes: int = 0

    @property
    def total_size_display(self) -> str:
        return format_size(self.total_size_bytes)


REGISTRY_SCAN_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE", 2),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node", 2),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE", 2),
    (winreg.HKEY_CLASSES_ROOT, r"", 1),
]


class ResidualScanner:
    _installed_paths_cache: Optional[Set[str]] = None
    _installed_paths_timestamp: float = 0.0

    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        self._callback = progress_callback

    def _emit(self, message: str, progress: int = -1):
        if self._callback:
            self._callback(message, progress)

    @classmethod
    def _get_installed_paths(cls) -> Set[str]:
        now = time.time()
        if cls._installed_paths_cache is not None and (now - cls._installed_paths_timestamp) < 30:
            return set(cls._installed_paths_cache)
        paths: Set[str] = set()
        try:
            scanner = SoftwareScanner()
            programs = scanner.scan_installed()
            for prog in programs:
                if prog.install_path and os.path.isdir(prog.install_path):
                    paths.add(os.path.normcase(os.path.normpath(prog.install_path)).rstrip("\\"))
        except Exception:
            pass
        cls._installed_paths_cache = paths
        cls._installed_paths_timestamp = now
        return set(paths)

    @staticmethod
    def _is_under_installed_path(path: str, installed_paths: Set[str]) -> bool:
        norm = os.path.normcase(os.path.normpath(path)).rstrip("\\")
        for ip in installed_paths:
            if norm == ip or norm.startswith(ip + "\\"):
                return True
        return False

    def scan(self, program: InstalledProgram) -> ResidualScanResult:
        result = ResidualScanResult(program_name=program.name)
        primary_kw, secondary_kw = self._generate_keywords(program)

        self._emit(f"正在扫描 {program.name} 的残留...", 0)

        self._emit("获取已安装软件路径...", 5)
        installed_paths = self._get_installed_paths()
        if program.install_path:
            norm = os.path.normcase(os.path.normpath(program.install_path)).rstrip("\\")
            installed_paths.discard(norm)

        self._emit("扫描注册表...", 10)
        result.registry_items = self._scan_registry(primary_kw, secondary_kw, installed_paths)
        self._emit(f"注册表扫描完成，发现 {len(result.registry_items)} 项", 40)

        self._emit("扫描文件系统...", 45)
        result.file_items = self._scan_filesystem(primary_kw, program, installed_paths)
        self._emit(f"文件扫描完成，发现 {len(result.file_items)} 项", 80)

        result.total_items = len(result.registry_items) + len(result.file_items)
        result.total_size_bytes = sum(
            item.size_bytes
            for item in result.registry_items + result.file_items
        )
        self._emit(f"扫描结束，共发现 {result.total_items} 项残留", 100)

        return result

    def _generate_keywords(self, program: InstalledProgram) -> tuple:
        primary = []
        secondary = []

        for name in [program.name, program.display_name]:
            if not name:
                continue
            primary.append(name.lower())

            parts = name.lower().replace(",", " ").replace(".", " ").replace("-", " ").split()
            for part in parts:
                if len(part) >= 4 and part not in primary:
                    primary.append(part)

            compact = name.lower().replace(" ", "").replace(".", "")
            if len(compact) >= 5 and compact not in primary:
                primary.append(compact)

        if program.publisher:
            pub_lower = program.publisher.lower()
            secondary.append(pub_lower)

            pub_parts = pub_lower.replace(",", " ").replace(".", " ").replace("-", " ").split()
            for part in pub_parts:
                if len(part) >= 4 and part not in secondary and part not in primary:
                    secondary.append(part)

        return primary, secondary

    def _scan_registry(self, primary_kw: List[str], secondary_kw: List[str],
                       installed_paths: Set[str]) -> List[ResidualItem]:
        items: List[ResidualItem] = []
        seen = set()

        for hive, base_path, max_depth in REGISTRY_SCAN_PATHS:
            base_key = open_key_safe(hive, base_path)
            if base_key is None:
                continue
            self._scan_registry_tree(hive, base_path, base_key, primary_kw,
                                     secondary_kw, max_depth, items, seen,
                                     installed_paths, 0)
            winreg.CloseKey(base_key)

        return items

    def _scan_registry_tree(self, hive: int, current_path: str, key: winreg.HKEYType,
                            primary_kw: List[str], secondary_kw: List[str],
                            max_depth: int,
                            items: List[ResidualItem], seen: set,
                            installed_paths: Set[str], depth: int):
        if current_path in seen:
            return
        seen.add(current_path)

        path_lower = current_path.lower()
        matched_by_primary = any(kw in path_lower for kw in primary_kw)
        matched_by_secondary = any(kw in path_lower for kw in secondary_kw)

        if matched_by_primary:
            items.append(ResidualItem(
                path=f"{self._hive_name(hive)}\\{current_path}",
                item_type="registry_key",
                description="包含软件名称的注册表项",
            ))
        elif matched_by_secondary and depth <= 1:
            pass

        for value_name in enum_values(key):
            vn_lower = value_name.lower()
            if any(kw in vn_lower for kw in primary_kw):
                full = f"{self._hive_name(hive)}\\{current_path} [{value_name}]"
                items.append(ResidualItem(
                    path=full,
                    item_type="registry_value",
                    description=f"包含软件名称的注册表值: {value_name}",
                ))

        if depth < max_depth:
            for sub_name in enum_keys(key):
                sub_path = f"{current_path}\\{sub_name}"
                sub_key = open_key_safe(hive, sub_path)
                if sub_key is not None:
                    self._scan_registry_tree(
                        hive, sub_path, sub_key, primary_kw, secondary_kw,
                        max_depth, items, seen, installed_paths, depth + 1
                    )
                    winreg.CloseKey(sub_key)

    def _hive_name(self, hive: int) -> str:
        names = {
            winreg.HKEY_LOCAL_MACHINE: "HKLM",
            winreg.HKEY_CURRENT_USER: "HKCU",
            winreg.HKEY_CLASSES_ROOT: "HKCR",
            winreg.HKEY_USERS: "HKU",
            winreg.HKEY_CURRENT_CONFIG: "HKCC",
        }
        return names.get(hive, "HK??")

    def _scan_filesystem(self, primary_kw: List[str],
                         program: InstalledProgram,
                         installed_paths: Set[str]) -> List[ResidualItem]:
        items: List[ResidualItem] = []

        dirs = find_directories_containing(RESIDUAL_COMMON_DIRS, primary_kw)
        for d in dirs:
            if self._is_under_installed_path(d, installed_paths):
                continue
            items.append(ResidualItem(
                path=d,
                item_type="directory",
                description="包含软件名称的目录",
                size_bytes=get_size(d),
            ))

        files = find_files_containing(RESIDUAL_COMMON_DIRS, primary_kw)
        for f in files:
            if self._is_under_installed_path(f, installed_paths):
                continue
            items.append(ResidualItem(
                path=f,
                item_type="file",
                description="包含软件名称的文件",
                size_bytes=get_size(f),
            ))

        return items

    def clean_selected(self, items: List[ResidualItem]) -> int:
        cleaned = 0
        for item in items:
            if not item.selected:
                continue
            if self._clean_item(item):
                cleaned += 1
        return cleaned

    def _clean_item(self, item: ResidualItem) -> bool:
        if item.item_type in ("registry_key", "registry_value"):
            return self._clean_registry_item(item)
        else:
            return safe_delete(item.path)

    def _clean_registry_item(self, item: ResidualItem) -> bool:
        if item.item_type == "registry_key":
            parsed = parse_reg_path(item.path)
            if parsed:
                from utils.registry import delete_key_tree
                return delete_key_tree(*parsed)

        if item.item_type == "registry_value":
            bracket = item.path.find(" [")
            if bracket > 0:
                key_path = item.path[:bracket]
                value_name = item.path[bracket + 2:-1]
                parsed = parse_reg_path(key_path)
                if parsed:
                    from utils.registry import delete_value_safe
                    return delete_value_safe(parsed[0], parsed[1], value_name)

        return False