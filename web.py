#!/usr/bin/env python3
"""
port_forwarder/web.py
=====================
English, minimal HTTP management UI for the Minecraft domain port forwarder.
"""

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from port_forwarder.config import Config
from port_forwarder.service_manager import (
    enable_autostart,
    disable_autostart,
    is_autostart_enabled,
    create_desktop_shortcut,
    run_service_now,
)

WEB_PORT = 25567


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MC Port Forwarder</title>
    <style>
        :root { --bg: #0f1115; --card: #181b21; --text: #e6e6e6; --muted: #8b929d; --accent: #3b82f6; --accent-h: #2563eb; --danger: #ef4444; --danger-h: #dc2626; --ok: #22c55e; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 32px 16px; }
        .wrap { max-width: 720px; margin: 0 auto; }
        h1 { font-size: 22px; margin: 0 0 4px; }
        .sub { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
        .card { background: var(--card); border: 1px solid #23262d; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
        .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        input, button { font-size: 14px; border-radius: 8px; border: none; outline: none; height: 38px; padding: 0 14px; }
        input { flex: 1; min-width: 140px; background: #111318; color: var(--text); border: 1px solid #2a2e36; }
        input::placeholder { color: #555; }
        input:focus { border-color: var(--accent); }
        button { background: var(--accent); color: #fff; cursor: pointer; font-weight: 500; white-space: nowrap; }
        button:hover { background: var(--accent-h); }
        button.danger { background: var(--danger); }
        button.danger:hover { background: var(--danger-h); }
        button.secondary { background: #2a2e36; color: var(--text); }
        button.secondary:hover { background: #333842; }
        button:disabled { opacity: .5; cursor: not-allowed; }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th { text-align: left; color: var(--muted); font-size: 12px; font-weight: 600; padding: 10px; border-bottom: 1px solid #2a2e36; }
        td { padding: 12px 10px; border-bottom: 1px solid #23262d; }
        .empty { color: var(--muted); padding: 18px 0; text-align: center; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .badge.on { background: rgba(34,197,94,.15); color: var(--ok); }
        .badge.off { background: rgba(239,68,68,.15); color: var(--danger); }
        .status-line { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .toast { position: fixed; top: 16px; right: 16px; background: var(--card); border: 1px solid #2a2e36; padding: 12px 16px; border-radius: 8px; font-size: 13px; box-shadow: 0 8px 24px rgba(0,0,0,.35); opacity: 0; transition: opacity .2s; pointer-events: none; }
        .toast.show { opacity: 1; }
    </style>
</head>
<body>
    <div class="wrap">
        <h1>Minecraft Domain Port Forwarder</h1>
        <div class="sub">Proxy listens on <strong>25565</strong> · Manage mappings below</div>

        <div class="card">
            <div class="status-line">
                <div>Auto-start: <span id="autoBadge" class="badge off">OFF</span></div>
                <div class="actions">
                    <button id="btnToggleAuto" onclick="toggleAutoStart()">Enable</button>
                    <button class="secondary" onclick="createShortcut()">Create Desktop Shortcut</button>
                    <button class="secondary" onclick="runNow()">Run Now</button>
                </div>
            </div>
            <div class="sub">Creates a hidden startup entry so the proxy runs without a command window.</div>
        </div>

        <div class="card">
            <div class="row">
                <input type="text" id="hostname" placeholder="oc.mc.rosebeg.com">
                <input type="number" id="port" placeholder="20202" style="flex: 0 0 120px;">
                <button onclick="addMapping()">Add Mapping</button>
            </div>
        </div>

        <div class="card">
            <table>
                <thead><tr><th>Domain</th><th>Local Port</th><th style="width:90px"></th></tr></thead>
                <tbody id="tbody"><tr><td colspan="3" class="empty">Loading...</td></tr></tbody>
            </table>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        const $ = id => document.getElementById(id);
        function toast(msg) {
            const t = $('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2500);
        }
        async function api(url, opts = {}) {
            const r = await fetch(url, opts);
            const text = await r.text();
            try { return { ok: r.ok, data: JSON.parse(text) }; }
            catch { return { ok: r.ok, data: text }; }
        }
        async function loadMappings() {
            const { data } = await api('/api/mappings');
            const tb = $('tbody');
            const keys = Object.keys(data).sort();
            tb.innerHTML = keys.length
                ? keys.map(h => `<tr><td>${h}</td><td>${data[h]}</td><td><button class="danger" onclick="del('${h}')">Delete</button></td></tr>`).join('')
                : '<tr><td colspan="3" class="empty">No mappings</td></tr>';
        }
        async function loadAutoStart() {
            const { data } = await api('/api/autostart/status');
            const on = data.enabled;
            $('autoBadge').textContent = on ? 'ON' : 'OFF';
            $('autoBadge').className = 'badge ' + (on ? 'on' : 'off');
            $('btnToggleAuto').textContent = on ? 'Disable' : 'Enable';
            $('btnToggleAuto').className = on ? 'danger' : '';
        }
        async function addMapping() {
            const h = $('hostname').value.trim().toLowerCase();
            const p = parseInt($('port').value);
            if (!h || !p) return toast('Enter domain and port');
            const { ok, data } = await api('/api/mappings', {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ hostname: h, port: p })
            });
            if (ok) { $('hostname').value = ''; $('port').value = ''; loadMappings(); toast('Added'); }
            else toast('Failed: ' + (data.error || data));
        }
        async function del(h) {
            const { ok } = await api('/api/mappings/' + encodeURIComponent(h), { method: 'DELETE' });
            if (ok) { loadMappings(); toast('Deleted'); }
        }
        async function toggleAutoStart() {
            const { data } = await api('/api/autostart/status');
            const url = data.enabled ? '/api/autostart/disable' : '/api/autostart/enable';
            const { ok, data: res } = await api(url, { method: 'POST' });
            if (ok) { loadAutoStart(); toast(data.enabled ? 'Auto-start disabled' : 'Auto-start enabled'); }
            else toast('Failed: ' + (res.error || res));
        }
        async function createShortcut() {
            const { ok, data } = await api('/api/shortcut/desktop', { method: 'POST' });
            toast(ok ? 'Desktop shortcut created' : 'Failed: ' + (data.error || data));
        }
        async function runNow() {
            const { ok, data } = await api('/api/service/run', { method: 'POST' });
            toast(ok ? 'Service started in background' : 'Failed: ' + (data.error || data));
        }
        loadMappings();
        loadAutoStart();
    </script>
</body>
</html>"""


def make_handler(config: Config):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send_json(self, status: int, data):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8"):
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send_json(200, {})

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self._send_text(200, HTML_PAGE, "text/html; charset=utf-8")
            elif parsed.path == "/api/mappings":
                self._send_json(200, config.list())
            elif parsed.path == "/api/autostart/status":
                self._send_json(200, {"enabled": is_autostart_enabled()})
            else:
                self._send_json(404, {"error": "Not Found"})

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)

            if parsed.path == "/api/mappings":
                self._handle_add_mapping()
            elif parsed.path == "/api/autostart/enable":
                try:
                    path = enable_autostart()
                    self._send_json(200, {"enabled": True, "path": str(path)})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            elif parsed.path == "/api/autostart/disable":
                try:
                    disable_autostart()
                    self._send_json(200, {"enabled": False})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            elif parsed.path == "/api/shortcut/desktop":
                try:
                    path = create_desktop_shortcut()
                    self._send_json(200, {"path": str(path)})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            elif parsed.path == "/api/service/run":
                try:
                    proc = run_service_now()
                    self._send_json(200, {"pid": proc.pid})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            else:
                self._send_json(404, {"error": "Not Found"})

        def _handle_add_mapping(self):
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                self._send_json(400, {"error": "Empty body"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                hostname = str(payload.get("hostname", "")).lower().strip()
                port = int(payload.get("port", 0))
            except Exception as e:
                self._send_json(400, {"error": f"Invalid JSON: {e}"})
                return

            if not hostname:
                self._send_json(400, {"error": "hostname is required"})
                return
            if not (1 <= port <= 65535):
                self._send_json(400, {"error": "port must be 1-65535"})
                return

            config.set(hostname, port)
            self._send_json(200, {"hostname": hostname, "port": port})

        def do_DELETE(self):
            parsed = urllib.parse.urlparse(self.path)
            prefix = "/api/mappings/"
            if not parsed.path.startswith(prefix):
                self._send_json(404, {"error": "Not Found"})
                return
            hostname = urllib.parse.unquote(parsed.path[len(prefix):])
            if config.delete(hostname):
                self._send_json(200, {"deleted": hostname})
            else:
                self._send_json(404, {"error": "Mapping not found"})

    return Handler


def start_web(config: Config, port: int = WEB_PORT):
    server = HTTPServer(("0.0.0.0", port), make_handler(config))
    print(f"[*] Web UI running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    from port_forwarder.config import Config
    start_web(Config())
