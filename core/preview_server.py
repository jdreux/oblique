"""Low-latency local preview streaming for headless Oblique rendering.

This module exposes a minimal HTTP server with:
- ``/``: tiny HTML viewer page
- ``/stream.mjpg``: multipart MJPEG stream
- ``/health``: JSON status endpoint
"""

from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import threading
import time
from typing import Optional

import numpy as np
from PIL import Image

from core.headless_renderer import HeadlessRenderer
from core.logger import info, warning
from core.oblique_patch import ObliquePatch


@dataclass
class _PreviewState:
    """Shared state between render and HTTP threads."""

    running: bool = True
    latest_jpeg: bytes = b""
    frame_index: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)
    cond: threading.Condition = field(init=False)

    def __post_init__(self) -> None:
        self.cond = threading.Condition(self.lock)

    def publish(self, jpeg_bytes: bytes) -> None:
        with self.cond:
            self.latest_jpeg = jpeg_bytes
            self.frame_index += 1
            self.cond.notify_all()

    def wait_for_frame(self, last_index: int, timeout: float) -> tuple[Optional[bytes], int]:
        with self.cond:
            if self.frame_index <= last_index and self.running:
                self.cond.wait(timeout=timeout)
            if self.frame_index <= last_index:
                return None, last_index
            return self.latest_jpeg, self.frame_index

    def stop(self) -> None:
        with self.cond:
            self.running = False
            self.cond.notify_all()


def _encode_jpeg(arr: np.ndarray, quality: int) -> bytes:
    rgb = (np.clip(arr[:, :, :3], 0.0, 1.0) * 255.0).astype(np.uint8)
    image = Image.fromarray(rgb, mode="RGB")
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=False,
        progressive=False,
    )
    return buffer.getvalue()


def _render_loop(
    state: _PreviewState,
    patch: ObliquePatch,
    width: int,
    height: int,
    fps: int,
    start_t: float,
    prime_audio: float,
    jpeg_quality: int,
    playback_speed: float,
) -> None:
    frame_period = 1.0 / fps
    try:
        with HeadlessRenderer(patch, width, height) as renderer:
            renderer.prime_audio(t=prime_audio)
            start_wall = time.perf_counter()
            next_frame_at = start_wall

            while state.running:
                now = time.perf_counter()
                t = start_t + (now - start_wall) * playback_speed
                arr = renderer.render_frame(t)
                state.publish(_encode_jpeg(arr, jpeg_quality))

                next_frame_at += frame_period
                sleep_for = next_frame_at - time.perf_counter()
                if sleep_for > 0.0:
                    time.sleep(sleep_for)
                else:
                    # If rendering falls behind, avoid large catch-up bursts.
                    next_frame_at = time.perf_counter()
    except Exception as exc:
        warning(f"[preview] render loop stopped: {exc}")
        state.stop()


def serve_preview(
    patch: ObliquePatch,
    width: int,
    height: int,
    host: str,
    port: int,
    fps: int,
    start_t: float,
    prime_audio: float,
    jpeg_quality: int,
    playback_speed: float,
) -> None:
    """Run a local preview server until interrupted."""
    state = _PreviewState()

    class _PreviewHandler(BaseHTTPRequestHandler):
        server_version = "ObliquePreview/1.0"

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - BaseHTTPRequestHandler API
            return

        def _write_html(self) -> None:
            body = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Oblique Preview</title>
    <style>
      body {{ margin: 0; background: #111; color: #ddd; font: 13px/1.4 monospace; }}
      .meta {{ padding: 8px 12px; border-bottom: 1px solid #222; }}
      img {{ display: block; width: min(100vw, {width}px); height: auto; margin: 0 auto; }}
    </style>
  </head>
  <body>
    <div class="meta">oblique preview @ {host}:{self.server.server_port} ({width}x{height} @ {fps} fps)</div>
    <img src="/stream.mjpg" alt="Oblique live preview" />
  </body>
</html>"""
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _write_health(self) -> None:
            payload = json.dumps({"ok": state.running, "fps": fps}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _write_stream(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Pragma", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            last_index = 0
            try:
                while state.running:
                    frame, last_index = state.wait_for_frame(last_index, timeout=1.0)
                    if frame is None:
                        continue
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path in {"/", "/index.html"}:
                self._write_html()
                return
            if self.path == "/health":
                self._write_health()
                return
            if self.path == "/stream.mjpg":
                self._write_stream()
                return

            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not found")

    httpd = ThreadingHTTPServer((host, port), _PreviewHandler)
    render_thread = threading.Thread(
        target=_render_loop,
        args=(
            state,
            patch,
            width,
            height,
            fps,
            start_t,
            prime_audio,
            jpeg_quality,
            playback_speed,
        ),
        daemon=True,
    )
    render_thread.start()

    bound_host, bound_port = httpd.server_address[0], httpd.server_address[1]
    info(f"[preview] Serving MJPEG stream at http://{bound_host}:{bound_port}/")
    try:
        httpd.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        info("[preview] Stopping preview server.")
    finally:
        state.stop()
        httpd.shutdown()
        httpd.server_close()
        render_thread.join(timeout=2.0)
