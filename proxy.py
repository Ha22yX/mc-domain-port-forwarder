"""
port_forwarder/proxy.py
=======================
Minecraft 基于握手包域名的 TCP 端口转发代理。

外部统一连接 25565，代理读取 Handshake 中的 server_address 字段，
根据配置表转发到不同的本地后端端口。
"""

import socket
import struct
import threading
import time

from port_forwarder.config import Config


MC_DEFAULT_PORT = 25565
BUFFER_SIZE = 65536
HANDSHAKE_TIMEOUT = 5.0


def decode_varint_from_bytes(data: bytes, idx: int):
    """从 bytes 中解码一个 varint，返回 (value, new_idx)。"""
    value = 0
    shift = 0
    while True:
        if idx >= len(data):
            raise ValueError("varint 不完整")
        b = data[idx]
        idx += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift >= 35:
            raise ValueError("varint 过长")
    return value, idx


def encode_varint(value: int) -> bytes:
    data = b""
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            data += bytes([byte | 0x80])
        else:
            data += bytes([byte])
            break
    return data


def parse_handshake(data: bytes):
    """
    解析 Minecraft Handshake 包（不含长度前缀）。
    返回 server_address 或 None。
    """
    try:
        idx = 0
        packet_id, idx = decode_varint_from_bytes(data, idx)
        if packet_id != 0x00:
            return None
        _protocol_version, idx = decode_varint_from_bytes(data, idx)
        addr_len, idx = decode_varint_from_bytes(data, idx)
        server_address = data[idx:idx + addr_len].decode("utf-8")
        # Forge 等会在域名后加 \0FML\0，取第一段即可
        server_address = server_address.split("\x00")[0].lower().strip()
        return server_address
    except Exception:
        return None


def read_handshake(sock: socket.socket) -> bytes:
    """从客户端 socket 读取完整 Handshake 包，返回原始包内容（不含长度前缀）。"""
    sock.settimeout(HANDSHAKE_TIMEOUT)
    # 读取包长度（varint）
    length = 0
    shift = 0
    while True:
        byte = sock.recv(1)
        if not byte:
            raise ConnectionResetError("连接在读取长度时断开")
        b = byte[0]
        length |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
        if shift >= 35:
            raise ValueError("包长度 varint 过长")

    if length <= 0 or length > 65535:
        raise ValueError(f"非法包长度: {length}")

    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionResetError("连接在读取握手包时断开")
        data += chunk
    return data


def build_disconnect(reason: str) -> bytes:
    """构造一个 Minecraft 断开连接包（next_state=2 时使用）。"""
    # 0x00 Login Disconnect, 但这里我们只做 status/login 通用的 Kick
    # 实际上如果握手后 next_state=2 我们应该发 Login Disconnect (0x00)
    # 内容格式: JSON 字符串
    import json
    reason_json = json.dumps({"text": reason})
    reason_bytes = reason_json.encode("utf-8")
    body = encode_varint(0x00) + encode_varint(len(reason_bytes)) + reason_bytes
    return encode_varint(len(body)) + body


def pipe(src: socket.socket, dst: socket.socket, name: str):
    """双向转发数据。"""
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            src.close()
        except OSError:
            pass
        try:
            dst.close()
        except OSError:
            pass


def handle_client(client_sock: socket.socket, client_addr, config: Config, listen_port: int):
    """处理一个外部客户端连接。"""
    try:
        handshake = read_handshake(client_sock)
        hostname = parse_handshake(handshake)

        if not hostname:
            print(f"[!] {client_addr[0]}:{client_addr[1]} 无法解析 Handshake，断开")
            client_sock.close()
            return

        backend_port = config.get(hostname)
        print(f"[*] {client_addr[0]}:{client_addr[1]} -> {hostname} -> 后端 127.0.0.1:{backend_port}")

        if backend_port is None:
            print(f"[!] 域名 {hostname} 没有配置映射")
            try:
                client_sock.sendall(build_disconnect(f"Unknown host: {hostname}"))
            except OSError:
                pass
            client_sock.close()
            return

        # 连接到本地后端
        backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_sock.settimeout(5.0)
        try:
            backend_sock.connect(("127.0.0.1", backend_port))
        except OSError as e:
            print(f"[!] 无法连接到后端 127.0.0.1:{backend_port}: {e}")
            try:
                client_sock.sendall(build_disconnect(f"Backend {backend_port} unreachable"))
            except OSError:
                pass
            client_sock.close()
            backend_sock.close()
            return

        # 先把握手包转发给后端（注意要加长度前缀）
        backend_sock.sendall(encode_varint(len(handshake)) + handshake)

        # 双向转发
        t1 = threading.Thread(target=pipe, args=(client_sock, backend_sock, "client->backend"), daemon=True)
        t2 = threading.Thread(target=pipe, args=(backend_sock, client_sock, "backend->client"), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except Exception as e:
        print(f"[!] 处理 {client_addr[0]}:{client_addr[1]} 时出错: {e}")
        try:
            client_sock.close()
        except OSError:
            pass


def start_proxy(config: Config, listen_port: int = MC_DEFAULT_PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", listen_port))
    server.listen(128)
    print(f"[*] MC 域名端口转发代理已启动: 0.0.0.0:{listen_port}")

    while True:
        client_sock, client_addr = server.accept()
        threading.Thread(target=handle_client,
                         args=(client_sock, client_addr, config, listen_port),
                         daemon=True).start()


if __name__ == "__main__":
    cfg = Config()
    start_proxy(cfg)
