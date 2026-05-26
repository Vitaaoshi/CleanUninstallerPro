import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from core.scanner import InstalledProgram


POTENTIAL_BUNDLE_SOFTWARE = {
    "McAfee": {
        "patterns": ["mcafee", "webadvisor", "siteadvisor", "livesafe", "total protection"],
        "risk": "high",
        "description": "McAfee 安全产品常随其他软件捆绑安装",
    },
    "Norton": {
        "patterns": ["norton", "symantec", "norton 360", "norton security"],
        "risk": "high",
        "description": "Norton 安全产品常随 OEM 软件捆绑安装",
    },
    "Avast": {
        "patterns": ["avast", "avast free antivirus", "avast secure browser", "avast cleanup"],
        "risk": "high",
        "description": "Avast 及其附加组件常随免费软件捆绑",
    },
    "AVG": {
        "patterns": ["avg", "avg antivirus", "avg secure browser", "avg tuneup", "avg zen"],
        "risk": "high",
        "description": "AVG 系列产品常随其他软件捆绑安装",
    },
    "CCleaner": {
        "patterns": ["ccleaner", "piriform"],
        "risk": "medium",
        "description": "CCleaner 有时会随其他工具软件捆绑",
    },
    "Driver Booster": {
        "patterns": ["driver booster", "driverbooster", "iobit"],
        "risk": "medium",
        "description": "Driver Booster 可能随其他 IObit 产品捆绑",
    },
    "Google Toolbar": {
        "patterns": ["google toolbar", "google toolbar for"],
        "risk": "low",
        "description": "Google 工具栏曾经常随软件捆绑安装",
    },
    "Ask Toolbar": {
        "patterns": ["ask toolbar", "ask.com", "askbar"],
        "risk": "high",
        "description": "Ask 工具栏是常见的捆绑软件",
    },
    "Yahoo Toolbar": {
        "patterns": ["yahoo toolbar", "yahoo! toolbar"],
        "risk": "medium",
        "description": "Yahoo 工具栏可能随旧版软件捆绑",
    },
    "Babylon Toolbar": {
        "patterns": ["babylon", "babylon toolbar"],
        "risk": "high",
        "description": "Babylon 工具栏是已知的 PUP（潜在不需要程序）",
    },
    "Bing Bar": {
        "patterns": ["bing bar", "bing toolbar"],
        "risk": "low",
        "description": "Bing Bar 可能随 Microsoft 产品安装",
    },
    "Bonjour": {
        "patterns": ["bonjour", "bonjour sdk"],
        "risk": "low",
        "description": "Bonjour 随 Apple 软件（iTunes 等）安装",
    },
    "Web Companion": {
        "patterns": ["web companion", "lavasoft", "webcompanion"],
        "risk": "high",
        "description": "Web Companion 常被标记为 PUP",
    },
    "Chromium": {
        "patterns": ["chromium", "ungoogled chromium"],
        "risk": "medium",
        "description": "第三方 Chromium 浏览器可能被篡改",
    },
    "Opera": {
        "patterns": ["opera browser", "opera stable", "opera gx"],
        "risk": "low",
        "description": "Opera 浏览器有时随免费工具捆绑推广",
    },
    "WinZip": {
        "patterns": ["winzip", "winzip driver updater"],
        "risk": "medium",
        "description": "WinZip 试用版或附加组件可能被捆绑",
    },
    "WinRAR": {
        "patterns": ["winrar"],
        "risk": "low",
        "description": "WinRAR 有时会通过第三方下载器捆绑",
    },
    "Dropbox": {
        "patterns": ["dropbox"],
        "risk": "low",
        "description": "Dropbox 有时随 OEM 系统预装",
    },
    "OneDrive": {
        "patterns": ["onedrive", "microsoft onedrive"],
        "risk": "low",
        "description": "OneDrive 随 Windows 系统预装",
    },
    "Cortana": {
        "patterns": ["cortana"],
        "risk": "low",
        "description": "Cortana 随 Windows 系统预装",
    },
    "Bloatware": {
        "patterns": ["pc app store", "pc cleaner", "driver updater", "registry cleaner",
                      "speedup", "optimizer pro", "system mechanic", "tuneup utilities"],
        "risk": "high",
        "description": "系统优化类软件，部分可能为潜在不需要程序",
    },
}


@dataclass
class BundleDetection:
    program: InstalledProgram
    bundle_name: str
    risk_level: str
    description: str
    matched_pattern: str


class BundleDetector:
    def __init__(self):
        self._bundle_db = POTENTIAL_BUNDLE_SOFTWARE

    def detect(self, programs: List[InstalledProgram]) -> List[BundleDetection]:
        detections: List[BundleDetection] = []
        seen: Set[str] = set()

        for program in programs:
            name_lower = program.name.lower()
            pub_lower = (program.publisher or "").lower()

            for bundle_name, bundle_info in self._bundle_db.items():
                for pattern in bundle_info["patterns"]:
                    if pattern in name_lower or pattern in pub_lower:
                        key = f"{program.name}|{bundle_name}"
                        if key in seen:
                            continue
                        seen.add(key)

                        detections.append(BundleDetection(
                            program=program,
                            bundle_name=bundle_name,
                            risk_level=bundle_info["risk"],
                            description=bundle_info["description"],
                            matched_pattern=pattern,
                        ))

        detections.sort(key=lambda d: {"high": 0, "medium": 1, "low": 2}[d.risk_level])
        return detections

    def get_risk_color(self, risk_level: str) -> str:
        return {"high": "#e74c3c", "medium": "#f39c12", "low": "#3498db"}.get(
            risk_level, "#95a5a6"
        )