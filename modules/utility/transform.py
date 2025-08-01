from dataclasses import dataclass
from typing import Tuple

import moderngl
import numpy as np

from modules.base_av_module import BaseAVModule, BaseAVParams, ParamTexture, Uniforms


@dataclass
class TransformParams(BaseAVParams):
    input_texture: ParamTexture  # Input texture to transform
    scale: Tuple[float, float] = (1.0, 1.0)  # 2D scale factors (x, y) - values >1 enlarge, <1 shrink
    angle: float = 0.0  # Rotation angle in degrees
    pivot: Tuple[float, float] = (0.5, 0.5)  # Pivot point for rotation (0-1 UV space)
    translate: Tuple[float, float] = (0.0, 0.0)  # Translation in UV space
    transform_order: str = "SRT"  # Scale, Rotate, Translate order


class TransformUniforms(Uniforms, total=True):
    u_transform_matrix: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]  # 3x3 matrix as mat3
    u_texture: BaseAVModule


class TransformModule(BaseAVModule[TransformParams, TransformUniforms]):
    """
    Transform module that applies affine transformations to UV coordinates.
    Supports scale, rotate, and translate operations using a 3x3 matrix.
    """

    metadata = {
        "name": "TransformModule",
        "description": "Applies affine transformations (scale, rotate, translate) to UV coordinates using a 3x3 matrix.",
        "parameters": {
            "input_texture": "ParamTexture",
            "scale": "Tuple[float, float]",
            "angle": "float",
            "pivot": "Tuple[float, float]",
            "translate": "Tuple[float, float]",
            "transform_order": "str",
        },
    }
    frag_shader_path: str = "modules/utility/transform.frag"

    def __init__(self, params: TransformParams):
        """
        Initialize Transform module.

        Args:
            params (TransformParams): Parameters for the transformation
        """
        super().__init__(params)

    def _build_transform_matrix(self) -> np.ndarray:
        """
        Build the 3x3 affine transformation matrix.

        Returns:
            np.ndarray: 3x3 transformation matrix
        """
        # Identity matrix
        matrix = np.eye(3)

        # Parse transform order (default: Scale, Rotate, Translate)
        order = self.params.transform_order.upper()

        for op in order:
            if op == "S":  # Scale
                sx, sy = self.params.scale
                scale = np.array([[sx, 0.0, 0.0],
                    [0.0, sy, 0.0],
                    [0.0, 0.0, 1.0]])

                # use pivot (same as rotation)
                pivot = np.array([[1, 0, -self.params.pivot[0]],
                    [0, 1, -self.params.pivot[1]],
                    [0, 0,  1]])
                pivot_inv = np.array([[1, 0,  self.params.pivot[0]],
                    [0, 1,  self.params.pivot[1]],
                    [0, 0,  1]])

                matrix = pivot_inv @ scale @ pivot @ matrix

            elif op == "R":  # Rotate
                # Convert degrees to radians
                angle_rad = np.radians(self.params.angle)
                cos_a = np.cos(angle_rad)
                sin_a = np.sin(angle_rad)

                # Move to pivot point
                pivot_matrix = np.array(
                    [
                        [1.0, 0.0, -self.params.pivot[0]],
                        [0.0, 1.0, -self.params.pivot[1]],
                        [0.0, 0.0, 1.0],
                    ]
                )

                # Rotate
                rotate_matrix = np.array(
                    [[cos_a, -sin_a, 0.0], [sin_a, cos_a, 0.0], [0.0, 0.0, 1.0]]
                )

                # Move back from pivot point
                pivot_inv_matrix = np.array(
                    [
                        [1.0, 0.0, self.params.pivot[0]],
                        [0.0, 1.0, self.params.pivot[1]],
                        [0.0, 0.0, 1.0],
                    ]
                )

                rotation_transform = pivot_inv_matrix @ rotate_matrix @ pivot_matrix
                matrix = rotation_transform @ matrix

            elif op == "T":  # Translate
                translate_matrix = np.array(
                    [
                        [1.0, 0.0, self.params.translate[0]],
                        [0.0, 1.0, self.params.translate[1]],
                        [0.0, 0.0, 1.0],
                    ]
                )
                matrix = translate_matrix @ matrix

        return matrix

    def prepare_uniforms(self, t: float) -> TransformUniforms:
        """
        Return uniforms with transformation matrix.

        Args:
            t (float): Current time

        Returns:
            Uniforms: Uniform values to pass to the shader
        """
        # Build transformation matrix
        transform_matrix = self._build_transform_matrix()

        # Flatten matrix to 9 floats for shader uniform (column-major for OpenGL)
        matrix_flattened = tuple(transform_matrix.flatten('F'))

        uniforms: TransformUniforms = {
            "u_resolution": self._resolve_resolution(),
            "u_transform_matrix": matrix_flattened,
            "u_texture": self.params.input_texture,
        }

        return uniforms


if __name__ == "__main__":
    # Test the transform module
    from modules.debug import DebugModule, DebugParams

    # Create a debug module as parent
    debug_params = DebugParams(width=800, height=600)
    debug_module = DebugModule(debug_params)

    params = TransformParams(
        width=800,
        height=600,
        input_texture=debug_module,
        scale=(1.5, 0.8),
        angle=17.0,  # 17 degrees (was 0.3 radians)
        pivot=(0.5, 0.5),
        translate=(0.1, -0.1),
        transform_order="SRT",
    )

    transform_module = TransformModule(params)

    print("Transform Module created successfully!")
    print(f"Parameters: {params}")
    print(f"Metadata: {transform_module.metadata}")
