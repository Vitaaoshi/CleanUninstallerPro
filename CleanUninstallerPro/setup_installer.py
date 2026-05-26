import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "CleanUninstaller Pro"
APP_VERSION = "v1.0"
PUBLISHER = "CleanUninstallerPro"
DEFAULT_DIR = os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "CleanUninstallerPro")

START_MENU_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    r"Microsoft\Windows\Start Menu\Programs",
    APP_NAME,
)
DESKTOP_DIR = os.path.join(
    os.environ.get("USERPROFILE", ""), "Desktop"
)


class InstallerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} {APP_VERSION} 安装程序")
        self.root.geometry("520x460")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f7fa")

        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.install_dir = tk.StringVar(value=DEFAULT_DIR)
        self.create_desktop = tk.BooleanVar(value=True)
        self.create_startmenu = tk.BooleanVar(value=True)
        self.install_status = tk.StringVar(value="")

        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg="#f5f7fa", padx=30, pady=20)
        main_frame.pack(fill="both", expand=True)

        tk.Label(
            main_frame, text=f"{APP_NAME} {APP_VERSION}",
            font=("Segoe UI", 18, "bold"), fg="#2c3e50", bg="#f5f7fa",
        ).pack(anchor="w", pady=(0, 4))

        tk.Label(
            main_frame,
            text="专业的 Windows 软件卸载与系统清理工具",
            font=("Segoe UI", 10), fg="#7f8c8d", bg="#f5f7fa",
        ).pack(anchor="w", pady=(0, 16))

        features = [
            "  •  安装监控 + 后台静默守护 + 开机自启",
            "  •  彻底扫描注册表与磁盘卸载残留",
            "  •  智能分类 + 暗色主题 + 收藏标记",
            "  •  垃圾/缓存/残留一键清理",
            "  •  批量卸载 + 强制移除",
        ]
        for f in features:
            tk.Label(
                main_frame, text=f,
                font=("Segoe UI", 9), fg="#5a6270", bg="#f5f7fa",
            ).pack(anchor="w")

        tk.Frame(main_frame, height=16, bg="#f5f7fa").pack()

        dir_frame = tk.Frame(main_frame, bg="#fff", highlightbackground="#dce1e6",
                             highlightthickness=1, padx=12, pady=12)
        dir_frame.pack(fill="x")

        tk.Label(dir_frame, text="安装目录", font=("Segoe UI", 10, "bold"),
                 fg="#2c3e50", bg="#fff").pack(anchor="w")

        dir_input_frame = tk.Frame(dir_frame, bg="#fff")
        dir_input_frame.pack(fill="x", pady=(6, 0))

        dir_entry = tk.Entry(dir_input_frame, textvariable=self.install_dir,
                             font=("Segoe UI", 9), bg="#f8f9fb",
                             relief="solid", bd=1)
        dir_entry.pack(side="left", fill="x", expand=True, ipady=4)

        browse_btn = tk.Button(dir_input_frame, text="浏览...",
                               font=("Segoe UI", 9), bg="#3498db", fg="#fff",
                               relief="flat", padx=14, pady=5,
                               activebackground="#2980b9",
                               command=self._browse_dir)
        browse_btn.pack(side="right", padx=(8, 0))

        tk.Frame(main_frame, height=12, bg="#f5f7fa").pack()

        opt_frame = tk.Frame(main_frame, bg="#f5f7fa")
        opt_frame.pack(fill="x")

        self.cb1 = tk.Checkbutton(
            opt_frame, text="创建桌面快捷方式", variable=self.create_desktop,
            font=("Segoe UI", 10), fg="#5a6270", bg="#f5f7fa",
            activebackground="#f5f7fa", selectcolor="#f5f7fa",
        )
        self.cb1.pack(anchor="w")

        self.cb2 = tk.Checkbutton(
            opt_frame, text="创建开始菜单快捷方式", variable=self.create_startmenu,
            font=("Segoe UI", 10), fg="#5a6270", bg="#f5f7fa",
            activebackground="#f5f7fa", selectcolor="#f5f7fa",
        )
        self.cb2.pack(anchor="w", pady=(2, 0))

        tk.Frame(main_frame, height=16, bg="#f5f7fa").pack()

        status_label = tk.Label(
            main_frame, textvariable=self.install_status,
            font=("Segoe UI", 9), fg="#27ae60", bg="#f5f7fa",
        )
        status_label.pack(fill="x")

        progress = ttk.Progressbar(main_frame, mode="indeterminate", length=400)

        btn_frame = tk.Frame(main_frame, bg="#f5f7fa")
        btn_frame.pack(fill="x", pady=(8, 0))

        self.install_btn = tk.Button(
            btn_frame, text="立即安装", font=("Segoe UI", 11, "bold"),
            bg="#3498db", fg="#fff", relief="flat",
            padx=32, pady=8, activebackground="#2980b9",
            command=self._do_install,
        )
        self.install_btn.pack(side="right", padx=(8, 0))

        cancel_btn = tk.Button(
            btn_frame, text="取消", font=("Segoe UI", 11),
            bg="#e0e4e8", fg="#2c3e50", relief="flat",
            padx=24, pady=8, activebackground="#d0d4d8",
            command=self._on_close,
        )
        cancel_btn.pack(side="right")

    def _browse_dir(self):
        result = filedialog.askdirectory(title="选择安装目录", initialdir=self.install_dir.get())
        if result:
            self.install_dir.set(result)

    def _on_close(self):
        if self.install_status.get():
            self.root.destroy()
        elif messagebox.askokcancel("取消安装", "确定要取消安装吗？"):
            self.root.destroy()

    def _get_bundled_dir(self) -> str:
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def _create_shortcut(self, target: str, shortcut_path: str, description: str = ""):
        try:
            import pythoncom
            from win32com.client import Dispatch

            pythoncom.CoInitialize()
            shell = Dispatch('WScript.Shell')
            sc = shell.CreateShortcut(shortcut_path)
            sc.TargetPath = target
            sc.WorkingDirectory = os.path.dirname(target)
            sc.Description = description or APP_NAME
            sc.Save()
        except Exception:
            pass

    def _do_install(self):
        target_dir = self.install_dir.get()

        if not os.path.isdir(os.path.dirname(target_dir.rstrip("\\"))):
            messagebox.showerror("错误", "所选安装目录的父目录不存在")
            return

        self.install_btn.config(state="disabled", text="正在安装...")
        self.install_status.set("正在准备安装...")
        self.root.update()

        try:
            os.makedirs(target_dir, exist_ok=True)

            bundled = self._get_bundled_dir()
            app_exe_src = os.path.join(bundled, "app_data", "CleanUninstallerPro.exe")
            bg_exe_src = os.path.join(bundled, "app_data", "CleanUninstallerPro_Bg.exe")

            if not os.path.isfile(app_exe_src):
                app_exe_src = os.path.join(bundled, "CleanUninstallerPro.exe")
            if not os.path.isfile(bg_exe_src):
                bg_exe_src = os.path.join(bundled, "CleanUninstallerPro_Bg.exe")

            self.install_status.set("正在复制文件...")
            self.root.update()

            if os.path.isfile(app_exe_src):
                shutil.copy2(app_exe_src, os.path.join(target_dir, "CleanUninstallerPro.exe"))
            else:
                messagebox.showerror("错误", f"未找到主程序: {app_exe_src}")
                self.install_btn.config(state="normal", text="立即安装")
                return

            if os.path.isfile(bg_exe_src):
                shutil.copy2(bg_exe_src, os.path.join(target_dir, "CleanUninstallerPro_Bg.exe"))

            self.install_status.set("正在创建快捷方式...")
            self.root.update()

            app_target = os.path.join(target_dir, "CleanUninstallerPro.exe")

            if self.create_startmenu.get():
                os.makedirs(START_MENU_DIR, exist_ok=True)
                self._create_shortcut(
                    app_target,
                    os.path.join(START_MENU_DIR, f"{APP_NAME}.lnk"),
                    f"{APP_NAME} - 软件卸载与系统清理工具",
                )

            if self.create_desktop.get():
                self._create_shortcut(
                    app_target,
                    os.path.join(DESKTOP_DIR, f"{APP_NAME}.lnk"),
                    f"{APP_NAME} - 软件卸载与系统清理工具",
                )

            self.install_status.set("正在进行最终设置...")
            self.root.update()

            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    0, winreg.KEY_SET_VALUE | winreg.KEY_CREATE_SUB_KEY,
                )
                sub_key = winreg.CreateKey(key, APP_NAME)
                winreg.SetValueEx(sub_key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
                winreg.SetValueEx(sub_key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
                winreg.SetValueEx(sub_key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
                winreg.SetValueEx(sub_key, "InstallLocation", 0, winreg.REG_SZ, target_dir)
                winreg.SetValueEx(sub_key, "UninstallString", 0, winreg.REG_SZ,
                                  f'"{app_target}" --uninstall')
                winreg.SetValueEx(sub_key, "DisplayIcon", 0, winreg.REG_SZ, app_target)
                winreg.SetValueEx(sub_key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(sub_key, "NoRepair", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(sub_key)
                winreg.CloseKey(key)
            except Exception:
                pass

            self.install_btn.config(text="安装完成 ✓", bg="#27ae60")
            self.install_status.set(f"已成功安装到: {target_dir}")
            self.root.update()

            messagebox.showinfo(
                "安装完成",
                f"{APP_NAME} 已成功安装！\n\n安装位置: {target_dir}\n\n"
                "您可以从开始菜单或桌面快捷方式启动程序。",
            )

        except Exception as e:
            messagebox.showerror("安装失败", f"安装过程中出现错误:\n{str(e)}")
            self.install_btn.config(state="normal", text="立即安装")
        finally:
            self.root.destroy()


def main():
    app = InstallerApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()