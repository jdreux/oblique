# modules/file_texture_module.py

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

import moderngl
from PIL import Image

from modules.core.base_av_module import BaseAVModule, BaseAVParams, Uniforms


class AspectMode(int, Enum):
    STRETCH = 0
    PRESERVE = 1
    COVER = 2
    FILL = 3

@dataclass(kw_only=True)
class MediaParams(BaseAVParams):
    file_path: str
    aspect_mode: AspectMode = AspectMode.PRESERVE

class MediaUniforms(Uniforms, total=True):
    u_resolution: Tuple[int, int]
    u_img_resolution: Tuple[int, int]
    u_aspect_mode: int
    u_transform: Tuple[float, float, float, float]  # scale_x, scale_y, offset_x, offset_y
    tex: moderngl.Texture

class MediaModule(BaseAVModule[MediaParams, MediaUniforms]):
    """
    Loads an image file and outputs it as a texture, with aspect ratio handling.
    """
    metadata = {
        "name": "FileTextureModule",
        "description": "Outputs a texture from an image file with aspect ratio handling.",
        "parameters": MediaParams.__annotations__,
    }
    frag_shader_path: str = "modules/core/media-module.frag"

    def __init__(self, params: MediaParams):
        super().__init__(params)
        self.aspect_mode = params.aspect_mode
        self.image = Image.open(self.params.file_path).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        self.img_width, self.img_height = self.image.size
        self.texture = None

    def _upload_texture(self, ctx: moderngl.Context):
        if self.texture is None:
            self.texture = ctx.texture(
                (self.img_width, self.img_height),
                4,
                self.image.tobytes(),
            )
            self.texture.build_mipmaps()
            self.texture.repeat_x = False
            self.texture.repeat_y = False

    def _compute_transform(self, width: int, height: int):
        # Returns (scale_x, scale_y, offset_x, offset_y) for the shader
        iw, ih = self.img_width, self.img_height
        ow, oh = width, height
        img_aspect = iw / ih
        out_aspect = ow / oh

        mode = self.aspect_mode
        if mode == AspectMode.STRETCH:
            return (1.0, 1.0, 0.0, 0.0)
        elif mode == AspectMode.PRESERVE:
            # Letterbox: fit inside, black bars
            if img_aspect > out_aspect:
                scale = out_aspect / img_aspect
                return (1.0, scale, 0.0, (1.0 - scale) / 2)
            else:
                scale = img_aspect / out_aspect
                return (scale, 1.0, (1.0 - scale) / 2, 0.0)
        elif mode == AspectMode.COVER:
            # Fill and crop (like CSS background-cover)
            if img_aspect > out_aspect:
                scale = img_aspect / out_aspect
                return (scale, 1.0, (1.0 - scale) / 2, 0.0)
            else:
                scale = out_aspect / img_aspect
                return (1.0, scale, 0.0, (1.0 - scale) / 2)
        elif mode == AspectMode.FILL:
            # Fill one dimension, leave leftover (no centering/cropping)
            if img_aspect > out_aspect:
                scale = out_aspect / img_aspect
                return (1.0, scale, 0.0, 0.0)
            else:
                scale = img_aspect / out_aspect
                return (scale, 1.0, 0.0, 0.0)
        else:
            return (1.0, 1.0, 0.0, 0.0)

    def prepare_uniforms(self, t: float) -> MediaUniforms:
        width = self._resolve_param(self.params.width)
        height = self._resolve_param(self.params.height)
        transform = self._compute_transform(width, height)
        assert self.texture is not None, "Media module texture is not loaded. Did you call render_texture()?"

        uniforms: MediaUniforms = {
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_img_resolution": (self.img_width, self.img_height),
            "u_aspect_mode": int(self.aspect_mode),
            "u_transform": transform,
            "tex": self.texture
        }
        return uniforms

    def render_texture(
        self,
        ctx: moderngl.Context,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        self._upload_texture(ctx)
        return super().render_texture(ctx, width, height, t)
