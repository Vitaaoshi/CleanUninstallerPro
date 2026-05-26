import winreg
from typing import Optional, List, Dict, Tuple


def open_key_safe(key: int, sub_key: str, access: int = winreg.KEY_READ) -> Optional[winreg.HKEYType]:
    try:
        return winreg.OpenKey(key, sub_key, 0, access | winreg.KEY_WOW64_64KEY)
    except OSError:
        try:
            return winreg.OpenKey(key, sub_key, 0, access | winreg.KEY_WOW64_32KEY)
        except OSError:
            return None


def enum_keys(key: winreg.HKEYType) -> List[str]:
    result = []
    i = 0
    while True:
        try:
            result.append(winreg.EnumKey(key, i))
            i += 1
        except OSError:
            break
    return result


def enum_values(key: winreg.HKEYType) -> Dict[str, Tuple[int, object]]:
    result = {}
    i = 0
    while True:
        try:
            name, value, value_type = winreg.EnumValue(key, i)
            result[name] = (value_type, value)
            i += 1
        except OSError:
            break
    return result


def get_value(key: winreg.HKEYType, name: str) -> Optional[Tuple[int, object]]:
    try:
        value, value_type = winreg.QueryValueEx(key, name)
        return (value_type, value)
    except OSError:
        return None


def delete_key_tree(root: int, sub_key: str) -> bool:
    try:
        winreg.DeleteKey(root, sub_key)
        return True
    except OSError:
        pass

    key = open_key_safe(root, sub_key, winreg.KEY_READ | winreg.KEY_WRITE)
    if key is None:
        return False
    try:
        for name in enum_keys(key):
            delete_key_tree(root, f"{sub_key}\\{name}")
    finally:
        winreg.CloseKey(key)

    try:
        winreg.DeleteKey(root, sub_key)
        return True
    except OSError:
        return False


def delete_value_safe(root: int, sub_key: str, value_name: str) -> bool:
    key = open_key_safe(root, sub_key, winreg.KEY_SET_VALUE)
    if key is None:
        return False
    try:
        winreg.DeleteValue(key, value_name)
        return True
    except OSError:
        return False
    finally:
        winreg.CloseKey(key)


HIVE_MAP = {
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
    "HKEY_USERS": winreg.HKEY_USERS,
    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}


def parse_reg_path(path: str) -> Optional[Tuple[int, str]]:
    for prefix, hive in sorted(HIVE_MAP.items(), key=lambda x: -len(x[0])):
        if path.upper().startswith(prefix.upper()):
            sub_key = path[len(prefix):].lstrip("\\")
            return (hive, sub_key)
    return None


def get_display_name(path: str) -> Optional[str]:
    parsed = parse_reg_path(path)
    if parsed is None:
        return None
    hive, sub_key = parsed
    key = open_key_safe(hive, sub_key)
    if key is None:
        return None
    val = get_value(key, "DisplayName")
    winreg.CloseKey(key)
    if val is None:
        return None
    return str(val[1]).strip() if val[1] else None