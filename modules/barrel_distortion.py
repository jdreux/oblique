from dataclasses import dataclass

import moderngl

from modules.base_av_module import BaseAVModule, BaseAVParams, RenderData, Uniforms


@dataclass
class BarrelDistortionParams(BaseAVParams):
    strength: float = 0.1  # Distortion strength (positive = barrel, negative = pincushion)
    center: tuple[float, float] = (0.5, 0.5)  # Center point for distortion (0-1 UV space)


class BarrelDistortionUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: tuple[int, int]
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
            "strength": "float",
            "center": "tuple[float, float]",
        },
    }
    frag_shader_path: str = "shaders/barrel-distortion.frag"

    def __init__(self, params: BarrelDistortionParams, parent_module: BaseAVModule):
        """
        Initialize Barrel Distortion module.

        Args:
            params (BarrelDistortionParams): Parameters for the distortion
            parent_module (BaseAVModule): Parent module to apply distortion to
        """
        super().__init__(params, parent_module)
        self.parent_module = parent_module

    def render_data(self, t: float) -> RenderData:
        """
        Return shader data with distortion parameters.

        Args:
            t (float): Current time

        Returns:
            dict[str, Any]: Shader path and uniforms
        """
        uniforms: BarrelDistortionUniforms = {
            "u_time": t,
            "u_resolution": (self.params.width, self.params.height),
            "u_strength": self.params.strength,
            "u_center": self.params.center,
            "u_texture": self.parent_tex,
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
        Render the barrel distortion module by first rendering the parent module to a texture,
        then applying the distortion shader using that texture as input.
        """
        self.parent_tex = self.parent_module.render_texture(ctx, width, height, t, filter)
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
        strength=0.2,  # Barrel distortion
        center=(0.5, 0.5),
    )

    barrel_module = BarrelDistortionModule(barrel_params, debug_module)

    print("Barrel Distortion Module created successfully!")
    print(f"Parameters: {barrel_params}")
    print(f"Metadata: {barrel_module.metadata}")
