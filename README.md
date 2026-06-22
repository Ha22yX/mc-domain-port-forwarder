# MC Domain Port Forwarder

A lightweight Minecraft Java Edition reverse proxy that routes external connections on port **25565** to different local backend ports based on the domain name in the Minecraft Handshake packet.

## Features

- **Domain-based forwarding**: `oc.mc.rosebeg.com` → `127.0.0.1:20202`, `gg.mc.rosebeg.com` → `127.0.0.1:1121`, etc.
- **Web UI**: Manage mappings at `http://127.0.0.1:25567`.
- **Auto start**: Enable/disable Windows startup entry from the web UI.
- **Desktop shortcut**: One-click shortcut that runs without a command window.
- **No external dependencies**: Uses only Python standard library.

## Quick Start

```bash
cd Desktop/tools
python -m port_forwarder.main
```

Then open `http://127.0.0.1:25567` in your browser.

## Requirements

- Windows (for auto-start / hidden-run features)
- Python 3.8+
- Administrator privileges (to bind port 25565)

## How It Works

Minecraft Java clients send a Handshake packet immediately after connecting. This packet contains the domain the player typed in. The proxy reads that domain and forwards the TCP stream to the matching local backend port.

```
Player: oc.mc.rosebeg.com:25565
            │
            ▼
    [Proxy 0.0.0.0:25565]
            │
            │ Handshake server_address = oc.mc.rosebeg.com
            ▼
    [Backend 127.0.0.1:20202]
```

## Network Setup

1. Point `*.mc.rosebeg.com` to your server's public IP via DNS.
2. Forward public TCP `25565` to this server's internal IP on port `25565`.
3. Run local Minecraft servers on their respective ports (e.g. `20202`, `1121`).
4. Allow inbound TCP `25565` through the Windows firewall.

## Project Structure

```text
port_forwarder/
├── main.py              # Entry point
├── proxy.py             # TCP proxy + Minecraft Handshake parser
├── web.py               # Web management UI (port 25567)
├── config.py            # Mapping persistence
├── service_manager.py   # Auto-start / shortcut / hidden run
├── run_service.vbs      # Auto-generated hidden launcher
└── README.md            # This file
```

## License

MIT
