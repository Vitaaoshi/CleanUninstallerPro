import winreg
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Set
from utils.registry import open_key_safe, enum_keys, enum_values, get_value
from utils.file_utils import get_size, format_size
from core.software_classifier import classify_program, is_system_software, load_favorites
from core.background_monitor import get_monitored_software_names, match_monitored_sessions_to_programs


def _get_dir_latest_mtime(path: str) -> float:
    latest = 0.0
    max_depth = 3
    base_sep = path.count(os.sep)
    try:
        for root, dirs, files in os.walk(path):
            depth = root.count(os.sep) - base_sep
            if depth >= max_depth:
                del dirs[:]
                continue
            try:
                mt = os.path.getmtime(root)
                if mt > latest:
                    latest = mt
            except OSError:
                pass
            for f in files:
                try:
                    mt = os.path.getmtime(os.path.join(root, f))
                    if mt > latest:
                        latest = mt
                except OSError:
                    pass
    except OSError:
        pass
    return latest


@dataclass
class InstalledProgram:
    name: str = ""
    version: str = ""
    publisher: str = ""
    install_path: str = ""
    uninstall_string: str = ""
    quiet_uninstall_string: str = ""
    registry_path: str = ""
    hive: str = ""
    size_bytes: int = 0
    install_date: str = ""
    icon_path: str = ""
    display_name: str = ""
    category: str = ""
    is_system: bool = False
    is_favorite: bool = False
    last_modified_days: int = 0
    is_monitored: bool = False

    @property
    def size_display(self) -> str:
        return format_size(self.size_bytes) if self.size_bytes > 0 else ""

    @property
    def is_valid(self) -> bool:
        return bool(self.name and self.name.strip())

    @property
    def is_unused(self) -> bool:
        return self.last_modified_days >= 180

    def enrich(self, favorites: Optional[Set[str]] = None):
        self.category = classify_program(self.name, self.publisher or "")
        self.is_system = is_system_software(self.name, self.publisher or "", self.install_path or "")
        if favorites is not None:
            self.is_favorite = self.name in favorites
        if self.install_path and os.path.isdir(self.install_path):
            latest = _get_dir_latest_mtime(self.install_path)
            if latest > 0:
                self.last_modified_days = int((time.time() - latest) / 86400)


UNINSTALL_PATHS_64 = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
)
UNINSTALL_PATHS_32 = (
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
)


class SoftwareScanner:
    def scan_installed(self) -> List[InstalledProgram]:
        programs: List[InstalledProgram] = []
        seen = set()
        favorites = load_favorites()

        hives = [
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", UNINSTALL_PATHS_64[0]),
            (winreg.HKEY_LOCAL_MACHINE, "HKLM", UNINSTALL_PATHS_32[0]),
            (winreg.HKEY_CURRENT_USER, "HKCU", UNINSTALL_PATHS_64[0]),
        ]

        for hive_root, hive_name, base_path in hives:
            base_key = open_key_safe(hive_root, base_path)
            if base_key is None:
                continue

            for sub_name in enum_keys(base_key):
                sub_key_path = f"{base_path}\\{sub_name}"
                sub_key = open_key_safe(hive_root, sub_key_path)
                if sub_key is None:
                    continue

                prog = self._parse_program(sub_key, sub_key_path, hive_name)
                winreg.CloseKey(sub_key)

                if not prog.is_valid:
                    continue

                identifier = f"{prog.name.lower()}|{prog.version.lower()}"
                if identifier in seen:
                    continue
                seen.add(identifier)

                if prog.install_path and prog.size_bytes == 0:
                    prog.size_bytes = get_size(prog.install_path)

                prog.enrich(favorites)
                programs.append(prog)

            winreg.CloseKey(base_key)

        programs.sort(key=lambda p: p.name.lower())

        monitored_names = match_monitored_sessions_to_programs(programs)
        for p in programs:
            p.is_monitored = p.name in monitored_names

        return programs

    def _parse_program(self, key: winreg.HKEYType, path: str, hive: str) -> InstalledProgram:
        prog = InstalledProgram(registry_path=path, hive=hive)
        values = enum_values(key)

        for name, (_, value) in values.items():
            if value is None:
                continue
            name_lower = name.lower()

            if name_lower == "displayname":
                prog.display_name = str(value).strip()
                if not prog.name:
                    prog.name = prog.display_name
            elif name_lower == "displayversion":
                prog.version = str(value).strip()
            elif name_lower == "publisher":
                prog.publisher = str(value).strip()
            elif name_lower == "installdir" or name_lower == "installlocation":
                prog.install_path = str(value).strip()
            elif name_lower == "uninstallstring":
                prog.uninstall_string = str(value).strip()
            elif name_lower == "quietuninstallstring":
                prog.quiet_uninstall_string = str(value).strip()
            elif name_lower == "installdate":
                prog.install_date = str(value).strip()
            elif name_lower == "displayicon":
                prog.icon_path = str(value).strip()
            elif name_lower == "estimatedsize":
                try:
                    prog.size_bytes = int(value) * 1024
                except (ValueError, TypeError):
                    pass

        if not prog.name:
            prog.name = prog.display_name or path.split("\\")[-1]

        return prog