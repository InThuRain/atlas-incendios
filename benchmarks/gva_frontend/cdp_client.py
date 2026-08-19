"""Minimal dependency-free Chrome DevTools Protocol client for local benchmarks."""

import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from urllib.parse import urlparse


class WebSocket:
    def __init__(self, url, timeout=150):
        parsed = urlparse(url)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout)
        self.socket.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Origin: http://127.0.0.1\r\n\r\n"
        ).format(parsed.path, parsed.hostname, parsed.port, key)
        self.socket.sendall(request.encode("ascii"))
        response = self._read_until(b"\r\n\r\n")
        if not response.startswith(b"HTTP/1.1 101"):
            raise RuntimeError("WebSocket handshake failed: {!r}".format(response[:200]))
        accept = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
        )
        if accept not in response:
            raise RuntimeError("WebSocket handshake returned an invalid accept key")

    def _read_until(self, marker):
        payload = bytearray()
        while marker not in payload:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket connection closed during handshake")
            payload.extend(chunk)
        return bytes(payload)

    def _read_exact(self, size):
        payload = bytearray()
        while len(payload) < size:
            chunk = self.socket.recv(size - len(payload))
            if not chunk:
                raise RuntimeError("WebSocket connection closed")
            payload.extend(chunk)
        return bytes(payload)

    def send_text(self, text):
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        length = len(payload)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(bytes(header) + mask + masked)

    def receive_text(self):
        fragments = []
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(length)
            if mask:
                payload = bytes(
                    value ^ mask[index % 4] for index, value in enumerate(payload)
                )
            if opcode == 0x8:
                raise RuntimeError("WebSocket closed by Chrome")
            if opcode == 0x9:
                self._send_control(0xA, payload)
                continue
            if opcode in (0x1, 0x0):
                fragments.append(payload)
                if final:
                    return b"".join(fragments).decode("utf-8")

    def _send_control(self, opcode, payload):
        mask = os.urandom(4)
        header = bytes([0x80 | opcode, 0x80 | len(payload)])
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(header + mask + masked)

    def close(self):
        try:
            self.socket.close()
        except OSError:
            pass


class CDPClient:
    def __init__(self, websocket_url):
        self.websocket = WebSocket(websocket_url)
        self.next_id = 1

    def command(self, method, params=None):
        command_id = self.next_id
        self.next_id += 1
        self.websocket.send_text(
            json.dumps({"id": command_id, "method": method, "params": params or {}})
        )
        while True:
            message = json.loads(self.websocket.receive_text())
            if message.get("id") == command_id:
                if "error" in message:
                    raise RuntimeError("CDP {}: {}".format(method, message["error"]))
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.command(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        remote = result["result"]
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return remote.get("value")

    def close(self):
        self.websocket.close()


def run_page(chrome, url, window_size, timeout=150, screenshot_path=None):
    with tempfile.TemporaryDirectory(prefix="atlas-cdp-") as profile:
        process = subprocess.Popen(
            [
                chrome,
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--enable-precise-memory-info",
                "--remote-debugging-port=0",
                "--remote-allow-origins=*",
                "--user-data-dir=" + profile,
                "--window-size=" + window_size,
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        client = None
        try:
            port_file = os.path.join(profile, "DevToolsActivePort")
            deadline = time.monotonic() + timeout
            while not os.path.exists(port_file):
                if process.poll() is not None:
                    raise RuntimeError("Chrome exited before opening DevTools")
                if time.monotonic() > deadline:
                    raise TimeoutError("Chrome DevTools port was not created")
                time.sleep(0.05)
            with open(port_file, "r", encoding="utf-8") as handle:
                port = int(handle.readline().strip())
            with urllib.request.urlopen(
                "http://127.0.0.1:{}/json/list".format(port), timeout=5
            ) as response:
                targets = json.load(response)
            page = next(target for target in targets if target["type"] == "page")
            client = CDPClient(page["webSocketDebuggerUrl"])
            client.command("Page.enable")
            client.command("Runtime.enable")
            client.command("Page.navigate", {"url": url})
            while True:
                complete = client.evaluate(
                    "document.querySelector('#debug-output')?.dataset.complete === 'true'"
                )
                if complete:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Frontend benchmark did not complete")
                time.sleep(0.05)
            text = client.evaluate(
                "document.querySelector('#debug-output').textContent"
            )
            if screenshot_path:
                screenshot = client.command(
                    "Page.captureScreenshot",
                    {"format": "png", "fromSurface": True},
                )
                with open(screenshot_path, "wb") as handle:
                    handle.write(base64.b64decode(screenshot["data"]))
            return json.loads(text)
        finally:
            if client:
                client.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            # Chrome helpers can finish flushing the temporary profile a few
            # milliseconds after the browser process exits.
            time.sleep(0.25)
