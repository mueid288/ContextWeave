"""E2E: shim rewrites and forwards to a mock upstream (stdlib, no GPU)."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
from urllib.request import Request, urlopen

from contextweave.product import proxy as proxy_mod
from contextweave.product.frequency import FrequencyPrior


def test_shim_forwards_stripped_body(monkeypatch):
    received: dict = {}

    class Upstream(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            received["body"] = json.loads(self.rfile.read(n).decode())
            received["path"] = self.path
            data = json.dumps(
                {
                    "id": "up",
                    "choices": [
                        {"message": {"role": "assistant", "content": "Karachi"}}
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):  # noqa: ANN002
            return

    up = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    up_port = up.server_address[1]

    monkeypatch.setenv("CW_UPSTREAM_URL", f"http://127.0.0.1:{up_port}")
    monkeypatch.setenv("CW_COLD_START_N", "0")
    monkeypatch.setenv("CW_CHUNK_ORDER", "by_frequency_desc")
    # reload module globals used by handler
    proxy_mod._UPSTREAM = f"http://127.0.0.1:{up_port}"
    proxy_mod._DEFAULT_MODE = "by_frequency_desc"
    proxy_mod._PRIOR = FrequencyPrior(cold_start_n=0)
    proxy_mod._PRIOR.observe(["hot"] * 5)

    shim = ThreadingHTTPServer(("127.0.0.1", 0), proxy_mod.OrderShimHandler)
    threading.Thread(target=shim.serve_forever, daemon=True).start()
    shim_port = shim.server_address[1]

    req_body = {
        "model": "m",
        "messages": [{"role": "user", "content": "What city?"}],
        "cw_documents": [
            {"document_id": "rare", "content": "Rare"},
            {"document_id": "hot", "content": "Hot city Karachi"},
        ],
        "cw_chunk_order": "by_frequency_desc",
    }
    data = json.dumps(req_body).encode()
    req = Request(
        f"http://127.0.0.1:{shim_port}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=10) as resp:
        out = json.loads(resp.read().decode())

    assert out["choices"][0]["message"]["content"] == "Karachi"
    assert "cw_documents" not in received["body"]
    assert "cw_meta" not in received["body"]
    content = received["body"]["messages"][0]["content"]
    assert content.index("hot") < content.index("rare") or content.index("Hot") < content.index(
        "Rare"
    )

    shim.shutdown()
    up.shutdown()
