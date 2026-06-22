"""
port_forwarder/config.py
========================
端口转发映射配置管理（JSON 持久化）。
"""

import json
import os
import threading

DEFAULT_CONFIG_PATH = "C:/Users/Administrator/Desktop/tools/port_forwarder/mappings.json"


class Config:
    def __init__(self, path: str = DEFAULT_CONFIG_PATH):
        self.path = path
        self.lock = threading.RLock()
        self.mappings = {}
        self.load()

    def load(self):
        with self.lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        self.mappings = json.load(f)
                except Exception:
                    self.mappings = {}
            else:
                self.mappings = {}

    def save(self):
        with self.lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)

    def get(self, hostname: str):
        with self.lock:
            return self.mappings.get(hostname)

    def set(self, hostname: str, backend_port: int):
        with self.lock:
            self.mappings[hostname] = backend_port
            self.save()

    def delete(self, hostname: str):
        with self.lock:
            if hostname in self.mappings:
                del self.mappings[hostname]
                self.save()
                return True
            return False

    def list(self):
        with self.lock:
            return dict(self.mappings)
