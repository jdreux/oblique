"""Shadertoy fragment shader importer module.

This module allows running Shadertoy‑style fragment shaders within Oblique by
mapping common uniforms used on shadertoy.com to the engine's data model. The
following uniforms are provided:

``iResolution`` – vec3 viewport resolution
``iTime`` – float time in seconds
``iChannel0..3`` – optional texture inputs
``audioTex`` – optional audio texture (e.g. FFT data)
"""

from dataclasses import dataclass
from typing import Tuple

import moderngl
from typing_extensions import TypedDict

from modules.core.base_av_module import (
    BaseAVModule,
    BaseAVParams,
    ParamTexture,
    Uniforms,
)


class ShadertoyUniforms(Uniforms, total=False):
    """TypedDict for uniforms supplied to Shadertoy shaders."""

    iResolution: Tuple[int, int, float]
    iTime: float
    iChannel0: moderngl.Texture
    iChannel1: moderngl.Texture
    iChannel2: moderngl.Texture
    iChannel3: moderngl.Texture
    audioTex: moderngl.Texture


@dataclass
class ShadertoyParams(BaseAVParams):
    """Parameters for :class:`ShadertoyModule`."""

    frag_shader_path: str
    iChannel0: ParamTexture | None = None
    iChannel1: ParamTexture | None = None
    iChannel2: ParamTexture | None = None
    iChannel3: ParamTexture | None = None
    audio_tex: ParamTexture | None = None


class ShadertoyModule(BaseAVModule[ShadertoyParams, ShadertoyUniforms]):
    """Render a Shadertoy fragment shader with minimal edits."""

    metadata = {
        "name": "ShadertoyModule",
        "description": (
            "Renders a Shadertoy fragment shader and maps common uniforms "
            "(iResolution, iTime, iChannel0..3, audioTex)."
        ),
        "parameters": ShadertoyParams.__annotations__,
    }

    def __init__(self, params: ShadertoyParams):
        # BaseAVModule expects ``frag_shader_path`` to be defined on the class, so
        # assign it before calling ``super().__init__``.
        self.frag_shader_path = params.frag_shader_path
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> ShadertoyUniforms:
        width = self._resolve_param(self.params.width)
        height = self._resolve_param(self.params.height)
        aspect = width / height if height else 1.0

        uniforms: ShadertoyUniforms = {
            "iResolution": (width, height, aspect),
            "iTime": t,
        }

        for idx in range(4):
            channel = getattr(self.params, f"iChannel{idx}")
            if channel is not None:
                uniforms[f"iChannel{idx}"] = channel  # type: ignore[index]

        if self.params.audio_tex is not None:
            uniforms["audioTex"] = self.params.audio_tex

        return uniforms
