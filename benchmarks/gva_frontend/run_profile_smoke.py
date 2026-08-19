#!/usr/bin/env python3
"""Verify development/public runtime manifests and the deny-by-default guard."""

import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from run_smoke import QuietHandler, chrome_snapshot, require


def main():
    root = Path(__file__).resolve().parents[2]
    runtime = root / "data/web/gva/manifest.json"
    development = runtime.read_bytes()
    handler = lambda *items, **kwargs: QuietHandler(*items, directory=str(root.parent), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/{root.name}/index.html"
    try:
        subprocess.run([sys.executable, str(root / "scripts/build_frontend_profile.py"), "--profile", "public", "--output", str(runtime)], check=True, stdout=subprocess.PIPE, text=True)
        payload = chrome_snapshot("/usr/bin/google-chrome", base + "?" + urlencode({"debug": 1}))
        final = payload["final"]
        require(final["profile"] == "public", "Public profile marker")
        require(final["activeSources"] == ["effis"], "Public profile must contain only EFFIS")
        require(final["visibleSigifRecordCount"] == 0, "Public profile must exclude SIGIF")
        require(final["visibleEffisPerimeterCount"] == 16, "Public EFFIS 2026")
        require(final["loader"]["requests"] == 2, "Public initial requests: manifest + EFFIS")
        blocked = subprocess.run([sys.executable, str(root / "scripts/build_frontend_profile.py"), "--profile", "public", "--include-source", "icv", "--output", str(runtime.with_suffix(".blocked.json"))], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        require(blocked.returncode != 0, "Public build must reject ICV")
        print(json.dumps({"status": "passed", "public_sources": final["activeSources"], "initial_requests": final["loader"]["requests"], "effis_2026": final["visibleEffisPerimeterCount"], "blocked_source_rejected": True}, indent=2))
    finally:
        runtime.write_bytes(development)
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
