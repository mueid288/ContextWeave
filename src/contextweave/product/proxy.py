"""Stdlib OpenAI-compatible shim: reorder docs, optional upstream forward.

No fastapi/httpx required. Laptop-safe (CPU). Upstream is whatever URL the
operator sets (typically a GPU host running vLLM OpenAI server).
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from contextweave.product.frequency import FrequencyPrior
from contextweave.product.live_order import apply_chat_documents

def _reload_runtime_from_env() -> None:
    """Refresh process globals from env (call after CLI sets CW_*)."""
    global _PRIOR, _UPSTREAM, _DEFAULT_MODE
    _PRIOR = FrequencyPrior(
        cold_start_n=int(os.environ.get("CW_COLD_START_N", "32")),
    )
    _UPSTREAM = os.environ.get("CW_UPSTREAM_URL", "").rstrip("/")
    _DEFAULT_MODE = os.environ.get("CW_CHUNK_ORDER", "by_frequency_desc")


_reload_runtime_from_env()


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _send_json(handler: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _forward(path: str, body: dict[str, Any], headers: dict[str, str]) -> tuple[int, bytes, str]:
    if not _UPSTREAM:
        raise RuntimeError("CW_UPSTREAM_URL is not set")
    url = f"{_UPSTREAM}{path}"
    # Strip cw_meta before upstream; engines may reject unknown fields.
    forward_body = {k: v for k, v in body.items() if k != "cw_meta"}
    data = json.dumps(forward_body).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(data)),
    }
    auth = headers.get("Authorization") or headers.get("authorization")
    if auth:
        req_headers["Authorization"] = auth
    req = Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urlopen(req, timeout=600) as resp:
            return resp.status, resp.read(), resp.headers.get("Content-Type", "application/json")
    except HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "application/json")


class OrderShimHandler(BaseHTTPRequestHandler):
    server_version = "ContextWeaveOrderShim/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # quieter than default
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/health", "/v1/cw/health"):
            _send_json(
                self,
                200,
                {
                    "ok": True,
                    "upstream": bool(_UPSTREAM),
                    "default_mode": _DEFAULT_MODE,
                    "prior_observations": _PRIOR.total_observations,
                    "prior_cold": _PRIOR.is_cold(),
                },
            )
            return
        _send_json(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = _read_json(self)
        except json.JSONDecodeError:
            _send_json(self, 400, {"error": "invalid json"})
            return

        if self.path in ("/v1/cw/reorder", "/reorder"):
            rewritten = apply_chat_documents(
                body, prior=_PRIOR, default_mode=_DEFAULT_MODE
            )
            _send_json(self, 200, rewritten)
            return

        if self.path.startswith("/v1/chat/completions"):
            rewritten = apply_chat_documents(
                body, prior=_PRIOR, default_mode=_DEFAULT_MODE
            )
            meta = rewritten.get("cw_meta")
            if not _UPSTREAM:
                # Dry live path: return rewrite only (no model).
                _send_json(
                    self,
                    200,
                    {
                        "id": "cw-dry-run",
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": (
                                        "[cw dry-run] no CW_UPSTREAM_URL; "
                                        "documents reordered only.\n"
                                        f"meta={json.dumps(meta)}"
                                    ),
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "cw_meta": meta,
                        "cw_rewritten_messages": rewritten.get("messages"),
                    },
                )
                return
            try:
                status, raw, ctype = _forward(
                    "/v1/chat/completions",
                    rewritten,
                    {k: v for k, v in self.headers.items()},
                )
            except (URLError, RuntimeError) as e:
                _send_json(self, 502, {"error": str(e), "cw_meta": meta})
                return
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-CW-Mode-Effective", str((meta or {}).get("cw_mode_effective")))
            self.end_headers()
            self.wfile.write(raw)
            return

        _send_json(self, 404, {"error": "not found"})


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    _reload_runtime_from_env()
    try:
        httpd = ThreadingHTTPServer((host, port), OrderShimHandler)
    except OSError as e:
        raise SystemExit(
            f"cw-serve-order failed to bind {host}:{port}: {e}\n"
            "Is another process using the port? "
            "Try: pkill -f cw-serve-order; ss -ltnp | grep 8080"
        ) from e
    print(
        f"cw-serve-order listening on http://{host}:{port} "
        f"upstream={_UPSTREAM or '(dry-run)'} mode={_DEFAULT_MODE} "
        f"cold_start_n={_PRIOR.cold_start_n}",
        flush=True,
    )
    httpd.serve_forever()
