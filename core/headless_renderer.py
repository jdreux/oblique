"""Headless rendering for Oblique.

Renders patches to images or video without a display or GLFW window.  Uses a
standalone ModernGL context (macOS CGL under the hood) so the full shader
pipeline runs on the GPU but no window ever appears.

Typical agent workflow::

    from core.headless_renderer import HeadlessRenderer
    from projects.demo.demo_audio_file import oblique_patch

    with HeadlessRenderer(oblique_patch(800, 600), 800, 600) as r:
        r.prime_audio(t=1.0)           # advance audio to t=1s
        r.render_to_file(1.0, "/tmp/frame.png")
        r.render_sequence([0, 1, 2], "/tmp/frames/")
        print(r.inspect(1.0))

CLI equivalent::

    oblique render projects.demo.demo_audio_file --t 1.0 --output /tmp/frame.png
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import moderngl
import numpy as np
from PIL import Image

from core.frame_analysis import analyze_frame, analyze_temporal
from core.logger import info, warning
from core.oblique_patch import ObliquePatch
from core.renderer import cleanup_last_good_cache, cleanup_shader_cache, cleanup_texture_cache, set_ctx


class HeadlessRenderer:
    """Render an :class:`~core.oblique_patch.ObliquePatch` to images or video without a display.

    Parameters
    ----------
    patch:
        An instantiated patch (the return value of a ``*_patch(width, height)`` factory).
    width:
        Render width in pixels.
    height:
        Render height in pixels.
    """

    def __init__(self, patch: ObliquePatch, width: int, height: int) -> None:
        self.patch = patch
        self.width = width
        self.height = height

        self.ctx: moderngl.Context = moderngl.create_context(standalone=True)
        set_ctx(self.ctx)

    # ------------------------------------------------------------------
    # Audio helpers
    # ------------------------------------------------------------------

    def prime_audio(self, t: float = 0.5) -> None:
        """Advance the audio input buffer to simulate playback up to time *t*.

        Calling this before ``render_frame`` populates the ring buffers used by
        processing operators (FFTBands, etc.) so that audio-reactive uniforms
        reflect the audio state at the given time offset rather than returning
        zeros.

        Parameters
        ----------
        t:
            Target time in seconds.  The audio buffer is advanced by
            ``int(t * sample_rate / chunk_size)`` read calls.
        """
        audio = self.patch.audio_output
        if audio is None:
            return

        audio.start()
        frames_to_skip = int(t * audio.sample_rate / audio.chunk_size)
        for _ in range(max(frames_to_skip, 1)):
            chunk = audio.read()
            if chunk.shape[0] == 0:
                break

    # ------------------------------------------------------------------
    # Core rendering
    # ------------------------------------------------------------------

    def render_frame(self, t: float) -> np.ndarray:
        """Render one frame and return an RGBA float32 array shaped ``(H, W, 4)``.

        Pixel values are in ``[0, 1]``.  The array is already Y-flipped so the
        top row of the image is index 0 (Pillow / standard convention).
        """
        module = self.patch.tick(t)
        tex = module.render_texture(self.ctx, self.width, self.height, t)
        raw = tex.read()
        arr = np.frombuffer(raw, dtype=np.float32).reshape(self.height, self.width, 4)
        return arr[::-1].copy()  # flip Y: OpenGL origin is bottom-left

    def render_to_image(self, t: float) -> Image.Image:
        """Render one frame and return a :class:`PIL.Image.Image` (RGBA)."""
        arr = self.render_frame(t)
        arr_uint8 = (np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8)
        return Image.fromarray(arr_uint8)

    def render_to_file(self, t: float, path: str) -> None:
        """Render one frame and save it to *path*.

        The format is inferred from the file extension (.png, .jpg, etc.).
        """
        self.render_to_image(t).save(path)
        info(f"[headless] Saved frame t={t:.3f}s → {path}")

    # ------------------------------------------------------------------
    # Multi-frame
    # ------------------------------------------------------------------

    def render_sequence(self, times: list[float], output_dir: str) -> list[str]:
        """Render one PNG per entry in *times* into *output_dir*.

        Files are named ``frame_NNNN.png`` with zero-padded indices.

        Returns a list of the written file paths.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        pad = max(4, len(str(len(times))))
        paths: list[str] = []
        for i, t in enumerate(times):
            dest = str(out / f"frame_{i:0{pad}d}.png")
            self.render_to_file(t, dest)
            paths.append(dest)

        info(f"[headless] Wrote {len(paths)} frames to {output_dir}")
        return paths

    def render_video(
        self,
        start_t: float,
        end_t: float,
        fps: int,
        output_path: str,
    ) -> None:
        """Render a video between *start_t* and *end_t* at *fps* frames per second.

        Requires ``ffmpeg`` to be available on PATH.  Raises :class:`RuntimeError`
        if it is not found.  The output format is inferred from the extension
        (.mp4, .mov, etc.) — H.264 is used for mp4/mov, palette-based encoding
        for .gif.

        Parameters
        ----------
        start_t:
            Start time in seconds.
        end_t:
            End time in seconds (exclusive).
        fps:
            Frames per second.
        output_path:
            Destination file path.
        """
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "ffmpeg not found on PATH. Install it to use render_video()."
            )

        n_frames = max(1, int((end_t - start_t) * fps))
        times = [start_t + i / fps for i in range(n_frames)]

        ext = Path(output_path).suffix.lower()
        if ext == ".gif":
            self._render_gif(times, fps, output_path)
        else:
            self._render_ffmpeg(times, fps, output_path)

    def _render_ffmpeg(self, times: list[float], fps: int, output_path: str) -> None:
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{self.width}x{self.height}",
            "-r", str(fps),
            "-i", "pipe:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            output_path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        assert proc.stdin is not None
        try:
            for t in times:
                arr = self.render_frame(t)
                rgb = (np.clip(arr[:, :, :3], 0.0, 1.0) * 255).astype(np.uint8)
                proc.stdin.write(rgb.tobytes())
        finally:
            proc.stdin.close()
            proc.wait()

        info(f"[headless] Video written → {output_path} ({len(times)} frames @ {fps} fps)")

    def _render_gif(self, times: list[float], fps: int, output_path: str) -> None:
        frames = [self.render_to_image(t).convert("RGB") for t in times]
        duration_ms = max(1, 1000 // fps)
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            loop=0,
            duration=duration_ms,
        )
        info(f"[headless] GIF written → {output_path} ({len(frames)} frames)")

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def inspect(self, t: float) -> dict:
        """Return rich visual statistics for a frame at time *t*.

        Useful for an AI agent to detect blank or broken output without
        loading the image file.

        Returns
        -------
        dict with keys:
            ``width`` and ``height`` plus the keys returned by
            :func:`core.frame_analysis.analyze_frame`.
        """
        arr = self.render_frame(t)
        stats = analyze_frame(arr)
        return {
            "width": self.width,
            "height": self.height,
            **stats,
        }

    def inspect_sequence(self, times: list[float]) -> dict:
        """Render a timeline and return frame + temporal analysis metrics."""
        if not times:
            raise ValueError("inspect_sequence requires at least one time sample.")

        frames = [self.render_frame(t) for t in times]
        frame_stats = analyze_frame(frames[-1])
        temporal_stats = analyze_temporal(frames)
        return {
            "width": self.width,
            "height": self.height,
            **frame_stats,
            **temporal_stats,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release GPU resources."""
        cleanup_shader_cache()
        cleanup_last_good_cache()
        cleanup_texture_cache()
        self.ctx.release()

    def __enter__(self) -> "HeadlessRenderer":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
