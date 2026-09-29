#!/usr/bin/env python3
"""Wait for TCP services without introducing another runtime dependency."""
from __future__ import annotations

import socket
import sys
import time


def wait_for(target: str, timeout: int = 90) -> None:
    host, raw_port = target.rsplit(":", 1)
    port = int(raw_port)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                print(f"Service ready: {host}:{port}")
                return
        except OSError:
            time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {host}:{port}")


if __name__ == "__main__":
    for service in sys.argv[1:]:
        wait_for(service)
