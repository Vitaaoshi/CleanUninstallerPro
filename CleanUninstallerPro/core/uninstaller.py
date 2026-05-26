import os
import subprocess
import tempfile
import time
import winreg
from typing import Optional, Callable
from core.scanner import InstalledProgram
from utils.registry import delete_key_tree, parse_reg_path
from utils.file_utils import safe_delete


class Uninstaller:
    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        self._callback = progress_callback

    def _emit(self, message: str, progress: int = -1):
        if self._callback:
            self._callback(message, progress)

    def uninstall(self, program: InstalledProgram) -> bool:
        self._emit(f"正在卸载: {program.name}", 10)

        if not program.uninstall_string and not program.quiet_uninstall_string:
            self._emit("错误: 未找到卸载信息", 100)
            return False

        uninstall_cmd = program.uninstall_string or program.quiet_uninstall_string
        success = self._execute_uninstall(uninstall_cmd, program)

        if success:
            self._emit("卸载完成", 100)
        else:
            self._emit("卸载可能未完全成功", 100)

        return success

    def _execute_uninstall(self, cmd: str, program: InstalledProgram) -> bool:
        cmd_expanded = os.path.expandvars(cmd)

        try:
            if cmd_expanded.lower().strip().startswith("msiexec"):
                args = cmd_expanded.split()
                full_args = args + ["/quiet", "/norestart"]
                proc = subprocess.run(
                    full_args,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return proc.returncode == 0 or proc.returncode == 3010
            else:
                exe_path, *args = self._parse_uninstall_cmd(cmd_expanded)
                if not exe_path:
                    return False

                proc = subprocess.Popen(
                    [exe_path] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                try:
                    proc.wait(timeout=300)
                    return proc.returncode == 0
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    return False
        except Exception:
            return False

    @staticmethod
    def _parse_uninstall_cmd(cmd: str):
        cmd = cmd.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 0:
                exe = cmd[1:end]
                rest = cmd[end + 1:].strip().split()
                return exe, rest
        parts = cmd.split(None, 1)
        if parts:
            exe = parts[0]
            rest = parts[1].split() if len(parts) > 1 else []
            return exe, rest
        return "", []

    def force_remove(self, program: InstalledProgram) -> bool:
        self._emit(f"正在强制移除: {program.name}", 20)

        if program.registry_path:
            parsed = parse_reg_path(program.registry_path)
            if parsed:
                hive, sub_key = parsed
                self._emit("正在删除注册表项...", 50)
                delete_key_tree(hive, sub_key)

        if program.install_path and os.path.isdir(program.install_path):
            self._emit("正在删除安装目录...", 70)
            safe_delete(program.install_path)

        self._emit("强制移除完成", 100)
        return True