#!/usr/bin/env python3
"""Capture desktop/mobile CV-1.5 screenshots after data loading completes."""

import argparse
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from cdp_client import run_page
from run_smoke import QuietHandler


def repository_root():
    return Path(__file__).resolve().parents[2]


def main():
    root = repository_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome", default="/usr/bin/google-chrome")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "data/derived/gva/frontend/screenshots",
    )
    args = parser.parse_args()
    handler = lambda *items, **kwargs: QuietHandler(
        *items, directory=str(root.parent), **kwargs
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = "http://127.0.0.1:{}/{}/index.html?{}".format(
        server.server_port, root.name, urlencode({"debug": 1})
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        for name, size in (("desktop", "1440,900"), ("mobile", "390,844")):
            path = args.output_dir / (name + ".png")
            run_page(args.chrome, base_url, size, screenshot_path=str(path))
            print(path)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
