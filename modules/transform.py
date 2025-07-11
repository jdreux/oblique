from dataclasses import dataclass
from typing import Any, Tuple
from modules.base_av_module import BaseAVModule, Uniforms, BaseAVParams
import numpy as np
import moderngl


@dataclass
class TransformParams(BaseAVParams):
    scale: Tuple[float, float] = (1.0, 1.0)  # 2D scale factors (x, y) - values >1 enlarge, <1 shrink
    angle: float = 0.0  # Rotation angle in degrees 
    pivot: Tuple[float, float] = (0.5, 0.5)  # Pivot point for rotation (0-1 UV space)
    translate: Tuple[float, float] = (0.0, 0.0)  # Translation in UV space
    transform_order: str = "SRT"  # Scale, Rotate, Translate order


class TransformUniforms(Uniforms, total=True):
    u_time: float
    u_resolution: Tuple[int, int]
    u_transform_matrix: Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]  # 3x3 matrix as mat3
    u_texture: moderngl.Texture


class TransformModule(BaseAVModule[TransformParams]):
    """
    Transform module that applies affine transformations to UV coordinates.
    Supports scale, rotate, and translate operations using a 3x3 matrix.
    """

    metadata = {
        "name": "TransformModule",
        "description": "Applies affine transformations (scale, rotate, translate) to UV coordinates using a 3x3 matrix.",
        "parameters": {
            "scale": "Tuple[float, float]",
            "angle": "float",
            "pivot": "Tuple[float, float]",
            "translate": "Tuple[float, float]",
            "transform_order": "str",
        },
    }
    frag_shader_path: str = "shaders/transform.frag"

    def __init__(self, params: TransformParams, upstream_module: BaseAVModule):
        """
        Initialize Transform module.

        Args:
            params (TransformParams): Parameters for the transformation
            upstream_module (BaseAVModule): Upstream module to transform
        """
        super().__init__(params, upstream_module)
        self.width = self.params.width
        self.height = self.params.height
        self.scale = self.params.scale
        self.angle = self.params.angle
        self.pivot = self.params.pivot
        self.translate = self.params.translate
        self.transform_order = self.params.transform_order
        self.upstream_module = upstream_module

    def _build_transform_matrix(self) -> np.ndarray:
        """
        Build the 3x3 affine transformation matrix.

        Returns:
            np.ndarray: 3x3 transformation matrix
        """
        # Identity matrix
        matrix = np.eye(3)

        # Parse transform order (default: Scale, Rotate, Translate)
        order = self.transform_order.upper()

        for op in order:
            if op == "S":  # Scale
                scale_matrix = np.array(
                    [
                        [self.scale[0], 0.0, 0.0],
                        [0.0, self.scale[1], 0.0],
                        [0.0, 0.0, 1.0],
                    ]
                )
                matrix = scale_matrix @ matrix

            elif op == "R":  # Rotate
                # Convert degrees to radians
                angle_rad = np.radians(self.angle)
                cos_a = np.cos(angle_rad)
                sin_a = np.sin(angle_rad)

                # Move to pivot point
                pivot_matrix = np.array(
                    [
                        [1.0, 0.0, -self.pivot[0]],
                        [0.0, 1.0, -self.pivot[1]],
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
                        [1.0, 0.0, self.pivot[0]],
                        [0.0, 1.0, self.pivot[1]],
                        [0.0, 0.0, 1.0],
                    ]
                )

                rotation_transform = pivot_inv_matrix @ rotate_matrix @ pivot_matrix
                matrix = rotation_transform @ matrix

            elif op == "T":  # Translate
                translate_matrix = np.array(
                    [
                        [1.0, 0.0, self.translate[0]],
                        [0.0, 1.0, self.translate[1]],
                        [0.0, 0.0, 1.0],
                    ]
                )
                matrix = translate_matrix @ matrix

        return matrix

    def render_data(self, t: float) -> dict[str, Any]:
        """
        Return shader data with transformation matrix.

        Args:
            t (float): Current time

        Returns:
            dict[str, Any]: Shader path and uniforms
        """
        # Build transformation matrix
        transform_matrix = self._build_transform_matrix()

        # Flatten matrix to 9 floats for shader uniform (column-major for OpenGL)
        matrix_flattened = tuple(transform_matrix.flatten('F'))

        uniforms: TransformUniforms = {
            "u_time": t,
            "u_resolution": (self.width, self.height),
            "u_transform_matrix": matrix_flattened,
            "u_texture": self.upstream_tex,
        }

        return {
            "frag_shader_path": self.frag_shader_path,
            "uniforms": uniforms,
        }

    def render_texture(
        self,
        ctx,
        width: int,
        height: int,
        t: float,
        filter=moderngl.NEAREST,
    ) -> moderngl.Texture:
        """
        Render the transform module by first rendering the upstream module to a texture,
        then applying the transform shader using that texture as input.
        """

        self.upstream_tex = self.upstream_module.render_texture(ctx, width, height, t, filter)
        # Render the module to a texture
        return super().render_texture(ctx, width, height, t)


if __name__ == "__main__":
    # Test the transform module
    params = TransformParams(
        width=800,
        height=600,
        scale=(1.5, 0.8),
        angle=17.0,  # 17 degrees (was 0.3 radians)
        pivot=(0.5, 0.5),
        translate=(0.1, -0.1),
        transform_order="SRT",
    )
