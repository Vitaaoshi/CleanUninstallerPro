import os
import shutil
import stat
import ctypes
from typing import List


def _remove_readonly(func, path, exc_info):
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        if attrs != 0xFFFFFFFF:
            ctypes.windll.kernel32.SetFileAttributesW(path, attrs & ~0x01)
        func(path)
    except Exception:
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass


def safe_delete(path: str) -> bool:
    if os.path.isfile(path) or os.path.islink(path):
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
            if attrs != 0xFFFFFFFF and (attrs & 0x01):
                ctypes.windll.kernel32.SetFileAttributesW(path, attrs & ~0x01)
            os.unlink(path)
            return True
        except OSError:
            try:
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)
                return True
            except OSError:
                return False
    elif os.path.isdir(path):
        try:
            shutil.rmtree(path, onerror=_remove_readonly)
            return True
        except OSError:
            return False
    return False


def find_directories_containing(base_dirs: List[str], keywords: List[str]) -> List[str]:
    found = []
    for base_dir in base_dirs:
        if not os.path.isdir(base_dir):
            continue
        for keyword in keywords:
            try:
                for entry in os.listdir(base_dir):
                    full_path = os.path.join(base_dir, entry)
                    if os.path.isdir(full_path) and keyword.lower() in entry.lower():
                        found.append(full_path)
            except OSError:
                continue
    return found


def find_files_containing(base_dirs: List[str], keywords: List[str]) -> List[str]:
    found = []
    for base_dir in base_dirs:
        if not os.path.isdir(base_dir):
            continue
        try:
            for root, dirs, files in os.walk(base_dir):
                depth = root[len(base_dir):].count(os.sep)
                if depth > 3:
                    del dirs[:]
                    continue
                for f in files:
                    full = os.path.join(root, f)
                    if any(kw.lower() in f.lower() for kw in keywords):
                        found.append(full)
        except OSError:
            continue
    return found


def get_size(path: str) -> int:
    total = 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    elif os.path.isdir(path):
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


RESIDUAL_COMMON_DIRS = list(
    d for d in (
        os.environ.get("PROGRAMDATA", "C:\\ProgramData"),
        os.environ.get("APPDATA", ""),
        os.environ.get("LOCALAPPDATA", ""),
        os.path.join(os.environ.get("APPDATA", ""), "..", "LocalLow") if os.environ.get("APPDATA") else "",
        os.environ.get("PROGRAMFILES", "C:\\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"),
    ) if d and os.path.isdir(d)
)