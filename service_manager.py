"""
port_forwarder/service_manager.py
=================================
管理开机自启动、桌面快捷方式、隐藏运行脚本等 Windows 平台相关功能。
"""

import os
import shutil
import socket
import subprocess
from pathlib import Path


def get_tools_dir() -> Path:
    """获取项目根目录 (Desktop/tools)。"""
    return Path(__file__).resolve().parent.parent


def get_startup_dir() -> Path:
    """获取当前用户的 Windows 启动目录。"""
    return Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))


def get_desktop_dir() -> Path:
    """获取当前用户桌面目录。"""
    return Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))


def get_vbs_path() -> Path:
    """隐藏运行的 VBS 启动脚本路径。"""
    return get_tools_dir() / "port_forwarder" / "start_hidden.vbs"


def generate_run_vbs() -> Path:
    """生成无窗口启动脚本 (start_hidden.vbs)。"""
    tools_dir = get_tools_dir()
    vbs_path = get_vbs_path()

    content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{tools_dir}"
WshShell.Run "python -m port_forwarder.main", 0, False
'''
    vbs_path.write_text(content, encoding="utf-8")
    return vbs_path


def is_autostart_enabled() -> bool:
    """检查是否已设置开机自启。"""
    startup = get_startup_dir()
    target = startup / "MC_Port_Forwarder.vbs"
    return target.exists()


def enable_autostart() -> Path:
    """设置开机自启动，返回启动目录中的 vbs 路径。"""
    vbs_path = generate_run_vbs()
    startup = get_startup_dir()
    startup.mkdir(parents=True, exist_ok=True)
    target = startup / "MC_Port_Forwarder.vbs"
    shutil.copy2(vbs_path, target)
    return target


def disable_autostart():
    """取消开机自启动。"""
    target = get_startup_dir() / "MC_Port_Forwarder.vbs"
    if target.exists():
        target.unlink()
    return not target.exists()


def create_desktop_shortcut() -> Path:
    """在桌面创建一键启动脚本（无窗口）。"""
    vbs_path = generate_run_vbs()
    desktop = get_desktop_dir()
    target = desktop / "Start MC Port Forwarder.vbs"
    shutil.copy2(vbs_path, target)
    return target


def is_port_in_use(port: int) -> bool:
    """检查本地端口是否已被占用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_service_now():
    """
    立即在后台无窗口启动服务。
    如果 25565 已被占用，抛出 RuntimeError。
    返回启动的进程对象。
    """
    if is_port_in_use(25565):
        raise RuntimeError("Port 25565 is already in use. Service is probably already running.")
    vbs_path = generate_run_vbs()
    return subprocess.Popen(
        ["wscript.exe", str(vbs_path)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
