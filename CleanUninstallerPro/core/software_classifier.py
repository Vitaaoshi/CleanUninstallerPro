import os
import json
from typing import Dict, List, Set, Optional

CATEGORY_RULES: Dict[str, Dict] = {
    "浏览器": {
        "keywords": {
            "chrome", "firefox", "browser", "opera", "edge", "brave",
            "vivaldi", "maxthon", "tor browser", "chromium",
        },
    },
    "安全软件": {
        "publishers": {
            "mcafee, llc", "nortonlifelock inc.", "symantec corporation",
            "avast software", "avg technologies", "kaspersky lab",
            "bitdefender", "eset", "trend micro", "malwarebytes",
            "crowd strike",
        },
        "keywords": {
            "antivirus", "anti-virus", "security", "firewall", "malware",
            "defender", "protection", "virus", "spyware", "360safe",
            "360security", "huorong",
        },
    },
    "开发工具": {
        "publishers": {
            "python software foundation", "jetbrains s.r.o.", "git for windows",
        },
        "keywords": {
            "python", "jdk", "java se", "java development", "node.js",
            "git", "docker", "vscode", "visual studio code",
            "visual studio", "eclipse", "intellij", "pycharm",
            "webstorm", "goland", "rustup", "compiler", "devenv",
            "codeblocks", "arduino", "anaconda", "miniconda",
            "conemu", "windows terminal", "powershell",
        },
    },
    "办公软件": {
        "publishers": {
            "kingsoft", "wps",
        },
        "keywords": {
            "microsoft office", "microsoft 365", "word", "excel", "powerpoint",
            "outlook", "onenote", "access", "publisher", "visio", "project",
            "wps office", "libreoffice", "openoffice", "notepad++",
            "acrobat", "adobe reader", "pdf", "foxit reader",
            "typora", "obsidian", "marktext",
        },
    },
    "图形设计": {
        "publishers": {
            "adobe inc.", "adobe systems", "autodesk", "corel corporation",
        },
        "keywords": {
            "photoshop", "illustrator", "premiere", "after effects",
            "blender", "gimp", "inkscape", "figma", "sketchup",
            "autocad", "3ds max", "maya", "coreldraw", "paint.net",
            "lightroom", "indesign", "davinci resolve",
        },
    },
    "影音娱乐": {
        "keywords": {
            "vlc", "spotify", "itunes", "music", "media player",
            "kodi", "plex", "netflix", "steam", "epic games", "gog",
            "obs studio", "audacity", "foobar2000", "aimp", "potplayer",
            "k-lite", "codec", "qq music", "netease cloud music",
        },
    },
    "网络工具": {
        "keywords": {
            "vpn", "proxy", "download manager", "torrent", "ftp",
            "putty", "winscp", "filezilla", "teamviewer", "anydesk",
            "idm", "thunder", "motrix", "clash", "v2ray",
        },
    },
    "压缩解压": {
        "keywords": {
            "winrar", "7-zip", "7zip", "winzip", "bandizip", "peazip",
            "haozip",
        },
    },
    "通讯社交": {
        "keywords": {
            "wechat", "qq", "skype", "zoom", "teams", "discord",
            "telegram", "whatsapp", "slack", "dingtalk", "feishu",
            "lark", "ding", "tencent meeting",
        },
    },
    "系统工具": {
        "keywords": {
            "driver", "firmware", "bios", "chipset", "runtime",
            "redistributable", "framework", "directx", "visual c++",
            ".net", "management engine", "c++ redistributable",
            "opencl runtime", "vcredist",
        },
    },
}

SYSTEM_SOFTWARE_PATTERNS: Set[str] = {
    "microsoft visual c++", "microsoft .net", "microsoft windows desktop runtime",
    "microsoft windows sdk", "microsoft vc redistributable", "microsoft xna",
    "microsoft mpi", "intel(r) management engine", "intel(r) graphics",
    "intel(r) processor", "intel(r) rapid storage", "intel(r) serial",
    "intel(r) chipset", "nvidia physx", "nvidia geforce experience",
    "realtek hd audio", "realtek ethernet", "realtek pcie",
    "amd chipset", "amd graphics", "amd raid",
    "windows driver", "driver update", "firmware update",
    "visual studio tools", "windows sdk",
    "directx runtime", "directx sdk", "opencl runtime",
    "microsoft application virtualization", "microsoft edge update",
    "microsoft update", "windows subsystem for linux",
}

CUSTOM_CATEGORY_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "CleanUninstallerPro", "custom_categories.json"
)

FAVORITES_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "CleanUninstallerPro", "favorites.json"
)

ALL_CATEGORIES = [
    "浏览器", "安全软件", "开发工具", "办公软件", "图形设计",
    "影音娱乐", "网络工具", "压缩解压", "通讯社交", "系统工具", "其他",
]

_custom_cache: Optional[Dict[str, str]] = None


def _load_custom_categories() -> Dict[str, str]:
    global _custom_cache
    if _custom_cache is not None:
        return _custom_cache
    try:
        if os.path.isfile(CUSTOM_CATEGORY_FILE):
            with open(CUSTOM_CATEGORY_FILE, "r", encoding="utf-8") as f:
                _custom_cache = json.load(f)
                return _custom_cache
    except Exception:
        pass
    _custom_cache = {}
    return _custom_cache


def _save_custom_categories(data: Dict[str, str]):
    global _custom_cache
    _custom_cache = data
    try:
        os.makedirs(os.path.dirname(CUSTOM_CATEGORY_FILE), exist_ok=True)
        with open(CUSTOM_CATEGORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def classify_program(name: str, publisher: str) -> str:
    custom = _load_custom_categories()
    if name in custom:
        return custom[name]

    name_lower = name.lower()
    pub_lower = (publisher or "").lower().strip()

    best_match = None
    best_score = 0

    for category, rules in CATEGORY_RULES.items():
        score = 0
        kw_match = any(kw in name_lower for kw in rules.get("keywords", set()))
        has_publishers = bool(rules.get("publishers"))
        pub_match = pub_lower in rules.get("publishers", set()) if has_publishers else False

        if kw_match and pub_match:
            score = 3
        elif kw_match:
            score = 2
        elif pub_match:
            score = 1

        if score > best_score:
            best_score = score
            best_match = category

    if best_match and best_score >= 1:
        return best_match
    return "其他"


def set_custom_category(name: str, category: str):
    custom = dict(_load_custom_categories())
    custom[name] = category
    _save_custom_categories(custom)


def remove_custom_category(name: str):
    custom = dict(_load_custom_categories())
    custom.pop(name, None)
    _save_custom_categories(custom)


def load_favorites() -> Set[str]:
    try:
        if os.path.isfile(FAVORITES_FILE):
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def save_favorites(favorites: Set[str]):
    try:
        os.makedirs(os.path.dirname(FAVORITES_FILE), exist_ok=True)
        with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(favorites)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def is_system_software(name: str, publisher: str, install_path: str = "") -> bool:
    name_lower = name.lower()
    pub_lower = (publisher or "").lower()

    for pattern in SYSTEM_SOFTWARE_PATTERNS:
        if pattern in name_lower:
            return True

    system_publishers = {
        "microsoft corporation", "intel corporation", "intel",
        "advanced micro devices, inc.", "amd",
        "nvidia corporation", "realtek semiconductor",
        "broadcom", "qualcomm atheros communications",
        "synaptics incorporated", "conexant systems",
    }
    if pub_lower in system_publishers:
        if any(kw in name_lower for kw in ["driver", "firmware", "chipset", "engine", "runtime"]):
            return True

    system_path_prefixes = [
        r"c:\windows",
        r"c:\program files\windowsapps",
        r"c:\program files (x86)\windowsapps",
    ]
    if install_path:
        install_lower = install_path.lower()
        for prefix in system_path_prefixes:
            if install_lower.startswith(prefix):
                return True

    return False


def get_publisher_groups(programs: list) -> Dict[str, list]:
    groups: Dict[str, list] = {}
    for prog in programs:
        pub = prog.publisher.strip() if prog.publisher else "未知发布者"
        if not pub:
            pub = "未知发布者"
        if pub not in groups:
            groups[pub] = []
        groups[pub].append(prog)
    return dict(sorted(groups.items(), key=lambda x: -len(x[1])))