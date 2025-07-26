from dataclasses import dataclass

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamTexture, RenderData, Uniforms


@dataclass
class BarrelDistortionParams(BaseAVParams):
    input_texture: ParamTexture  # Input texture to apply distortion to
    strength: ParamFloat = 0.1  # Distortion strength (positive = barrel, negative = pincushion)
    center: tuple[ParamFloat, ParamFloat] = (0.5, 0.5)  # Center point for distortion (0-1 UV space)


class BarrelDistortionUniforms(Uniforms, total=True):
    u_strength: float
    u_center: tuple[float, float]
    u_texture: moderngl.Texture


class BarrelDistortionModule(BaseAVModule[BarrelDistortionParams]):
    """
    Barrel/Pincushion distortion module that applies radial distortion to UV coordinates.
    Positive strength values create barrel distortion (bulging outward).
    Negative strength values create pincushion distortion (pinching inward).
    """

    metadata = {
        "name": "BarrelDistortionModule",
        "description": "Applies barrel or pincushion distortion to UV coordinates using radial transformation.",
        "parameters": {
            "input_texture": "ParamTexture",
            "strength": "float",
            "center": "tuple[float, float]",
        },
    }
    frag_shader_path: str = "shaders/barrel-distortion.frag"

    def __init__(self, params: BarrelDistortionParams):
        """
        Initialize Barrel Distortion module.

        Args:
            params (BarrelDistortionParams): Parameters for the distortion
        """
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> RenderData:
        """
        Return shader data with distortion parameters.

        Args:
            t (float): Current time

        Returns:
            dict[str, Any]: Shader path and uniforms
        """
        uniforms: BarrelDistortionUniforms = {
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_strength": self._resolve_param(self.params.strength),
            "u_center": (self._resolve_param(self.params.center[0]), self._resolve_param(self.params.center[1])),
            "u_texture": self.input_tex,
        }

        return RenderData(
            frag_shader_path=self.frag_shader_path,
            uniforms=uniforms,
        )

    def render_texture(
        self,
        ctx,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Render the barrel distortion module by first rendering the input texture,
        then applying the distortion shader using that texture as input.
        """
        self.input_tex = self._resolve_texture_param(self.params.input_texture, ctx, width, height, t, filter)
        # Render the module to a texture
        return super().render_texture(ctx, width, height, t)


if __name__ == "__main__":
    # Test the barrel distortion module
    from modules.debug import DebugModule, DebugParams

    # Create a debug module as parent
    debug_params = DebugParams(width=800, height=600)
    debug_module = DebugModule(debug_params)

    # Create barrel distortion module
    barrel_params = BarrelDistortionParams(
        width=800,
        height=600,
        input_texture=debug_module,
        strength=0.2,  # Barrel distortion
        center=(0.5, 0.5),
    )

    barrel_module = BarrelDistortionModule(barrel_params)

    print("Barrel Distortion Module created successfully!")
    print(f"Parameters: {barrel_params}")
    print(f"Metadata: {barrel_module.metadata}")
