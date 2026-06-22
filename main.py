#!/usr/bin/env python3
"""
port_forwarder/main.py
======================
启动 MC 域名端口转发服务。
- 25565: Minecraft TCP 代理（根据握手包域名转发）
- 25567: 网页管理界面

用法:
    cd Desktop/tools
    python -m port_forwarder.main
"""

import sys
import threading
from pathlib import Path

# 允许从任意目录启动：把项目根目录 (Desktop/tools) 加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from port_forwarder.config import Config
from port_forwarder.proxy import start_proxy
from port_forwarder.web import start_web


def main():
    config = Config()

    proxy_thread = threading.Thread(target=start_proxy, args=(config, 25565), daemon=True)
    web_thread = threading.Thread(target=start_web, args=(config, 25567), daemon=True)

    proxy_thread.start()
    web_thread.start()

    print("=" * 60)
    print("Minecraft 域名端口转发服务已启动")
    print("代理端口: 25565")
    print("管理页面: http://127.0.0.1:25567")
    print("按 Ctrl+C 停止")
    print("=" * 60)

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] 服务已停止")


if __name__ == "__main__":
    main()
