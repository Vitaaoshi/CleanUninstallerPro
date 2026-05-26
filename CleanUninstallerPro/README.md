# CleanUninstaller Pro v1.0

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey.svg)]()

专业的 Windows 软件卸载与系统清理工具，类似 IObit Uninstaller，支持安装监控、注册表/磁盘残留彻底扫描、批量卸载、垃圾清理等功能。

## ✨ 核心功能

- **🔍 安装监控** — 实时追踪软件安装过程中的文件系统变更，记录所有新增/修改的文件和注册表项
- **🛡️ 后台静默守护** — 系统托盘后台运行，自动检测新软件安装，支持开机自启
- **🧹 彻底卸载** — 先调用软件自带卸载程序，再深度扫描注册表和磁盘残留
- **📋 智能分类** — 自动识别软件类别（系统工具、办公软件、游戏等），支持手动修改分类
- **⭐ 收藏标记** — 标记常用软件，检测超半年未使用的闲置应用
- **🗑️ 垃圾清理** — 临时文件、浏览器缓存、系统缓存、回收站、卸载残留、日志文件共 6 类清理
- **🎨 暗色/亮色主题** — 现代化扁平 UI，一键切换
- **📦 批量操作** — 支持批量卸载、强制移除顽固软件
- **🔑 筛选与排序** — 按分类、发布者、安装日期、文件大小筛选和排序

## 🖥️ 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 (64位) |
| Python | 3.12+ (仅开发/源码运行需要) |

## 📥 下载与使用

### 方式一：安装包（推荐）

下载 [CleanUninstallerPro_Setup.exe](https://github.com/Vitaaoshi/CleanUninstallerPro/releases)，以管理员身份运行安装程序，自动创建桌面/开始菜单快捷方式并注册到控制面板。

### 方式二：便携版

直接下载 [CleanUninstallerPro.exe] [CleanUninstallerPro_Bg.exe] (https://github.com/Vitaaoshi/CleanUninstallerPro/releases) 运行，无需安装，即开即用。

### 方式三：从源码运行

```bash
git clone https://github.com/Vitaaoshi/CleanUninstallerPro.git
cd CleanUninstallerPro
pip install -r requirements.txt
python main.py
```

## 📂 项目结构

```
CleanUninstallerPro/
├── main.py                    # 主程序入口
├── bg_service.py              # 后台监控服务入口
├── setup_installer.py         # 安装程序
├── gui/
│   ├── main_window.py         # 主窗口 UI
│   └── residual_dialog.py     # 残留扫描对话框
├── core/
│   ├── scanner.py             # 已安装软件扫描
│   ├── uninstaller.py         # 卸载引擎
│   ├── residual_scanner.py    # 残留文件扫描
│   ├── install_monitor.py     # 安装过程监控
│   ├── background_monitor.py  # 后台静默监控
│   ├── junk_cleaner.py        # 垃圾清理引擎
│   └── software_classifier.py # 软件分类引擎
├── utils/
│   ├── registry.py            # 注册表工具
│   └── file_utils.py          # 文件操作工具
├── requirements.txt
└── LICENSE
```

## 🔨 自行打包

```bash
# 便携版
pyinstaller CleanUninstallerPro.spec --clean --noconfirm

# 后台服务
pyinstaller CleanUninstallerPro_Bg.spec --clean --noconfirm

# 安装包（需要先完成前两步）
pyinstaller installer.spec --clean --noconfirm
```

## ⚠️ 免责声明

本软件仅用于合法的软件管理与系统清理目的。使用者应自行承担使用风险：

1. **卸载操作不可逆**：请在卸载前确认要移除的软件，建议重要软件提前备份
2. **残留清理需谨慎**：自动扫描结果可能存在误报，请逐项确认后再删除
3. **管理员权限**：部分功能需要管理员权限才能正常运行
4. **杀毒软件**：本软件经过安全编码（无 shell 执行、无隐藏窗口），如遇误报请添加信任

**开发者不承担因使用本软件而导致的任何直接或间接损失。**

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

<p align="center">
  Copyright &copy; 2026 白衣傲世 | <a href="https://github.com/Vitaaoshi">GitHub: Vitaaoshi</a>
</p>
