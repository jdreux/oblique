from dataclasses import dataclass

import moderngl

from modules.core.base_av_module import BaseAVModule, BaseAVParams, ParamFloat, ParamTexture, Uniforms


@dataclass
class BarrelDistortionParams(BaseAVParams):
    input_texture: ParamTexture  # Input texture to apply distortion to
    strength: ParamFloat = 0.1  # Distortion strength (positive = barrel, negative = pincushion)
    center: tuple[ParamFloat, ParamFloat] = (0.5, 0.5)  # Center point for distortion (0-1 UV space)


class BarrelDistortionUniforms(Uniforms, total=True):
    u_strength: float
    u_center: tuple[float, float]
    u_texture: moderngl.Texture | BaseAVModule


class BarrelDistortionModule(BaseAVModule[BarrelDistortionParams, BarrelDistortionUniforms]):
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
    frag_shader_path: str = "modules/effects/barrel-distortion.frag"

    def __init__(self, params: BarrelDistortionParams):
        """
        Initialize Barrel Distortion module.

        Args:
            params (BarrelDistortionParams): Parameters for the distortion
        """
        super().__init__(params)

    def prepare_uniforms(self, t: float) -> BarrelDistortionUniforms:
        """
        Return uniforms with distortion parameters.

        Args:
            t (float): Current time

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        uniforms: BarrelDistortionUniforms = {
            "u_resolution": (self._resolve_param(self.params.width), self._resolve_param(self.params.height)),
            "u_strength": self._resolve_param(self.params.strength),
            "u_center": (self._resolve_param(self.params.center[0]), self._resolve_param(self.params.center[1])),
            "u_texture": self.params.input_texture,
        }

        return uniforms

if __name__ == "__main__":
    # Test the barrel distortion module
    from modules.utility.debug import DebugModule, DebugParams

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
