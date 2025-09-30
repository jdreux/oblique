"""
Shader pre-processor for handling #include directives.

This module provides functionality to pre-process GLSL shaders by resolving
#include directives and handling circular dependencies.
"""

import re
from pathlib import Path
from typing import List, Optional, Set, Union

from core.paths import resolve_asset_path


class ShaderPreprocessor:
    """
    Pre-processor for GLSL shaders that handles #include directives.
    
    Supports:
    - #include "path/to/file.glsl" (relative to shader directory)
    - #include <lygia/path/to/file.glsl> (from lygia library)
    - Circular dependency detection
    - Include path resolution
    """

    def __init__(
        self,
        shader_dir: Union[str, Path, None] = None,
        lygia_dir: Union[str, Path, None] = None,
    ):
        """
        Initialize the pre-processor.
        
        Args:
            shader_dir: Directory containing shader files
            lygia_dir: Directory containing lygia library files
        """
        shader_root = resolve_asset_path("shaders") if shader_dir is None else Path(shader_dir)
        lygia_root = resolve_asset_path("external/lygia") if lygia_dir is None else Path(lygia_dir)
        self.shader_dir = shader_root
        self.lygia_dir = lygia_root
        self._processed_files: Set[str] = set()
        self._include_stack: List[str] = []

    def preprocess_shader(self, shader_path: str) -> str:
        """
        Pre-process a shader file, resolving all #include directives.
        
        Args:
            shader_path: Path to the shader file to pre-process
            
        Returns:
            Pre-processed shader source code
            
        Raises:
            FileNotFoundError: If an included file cannot be found
            RuntimeError: If circular dependencies are detected
        """
        self._processed_files.clear()
        self._include_stack.clear()

        result = self._process_file(shader_path)

        # Debug: Print the final resolved shader content
        # print("=" * 80)
        # print(f"FINAL RESOLVED SHADER: {shader_path}")
        # print("=" * 80)
        # print(result)
        # print("=" * 80)

        return result

    def _process_file(self, file_path: str) -> str:
        """
        Process a single file, handling includes recursively.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Processed file content
        """
        # Detect circular dependencies
        if file_path in self._include_stack:
            stack_str = " -> ".join(self._include_stack + [file_path])
            raise RuntimeError(f"Circular dependency detected: {stack_str}")

        self._include_stack.append(file_path)

        try:
            # Read the file content
            full_path = self._resolve_path(file_path)
            if not full_path.exists():
                raise FileNotFoundError(f"Shader file not found: {file_path}")

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Process includes
            processed_content = self._process_includes(content, full_path.parent)

            return processed_content

        finally:
            self._include_stack.pop()

    def _process_includes(self, content: str, base_dir: Path) -> str:
        """
        Process #include directives in the content.
        
        Args:
            content: Shader source code
            base_dir: Base directory for relative includes
            
        Returns:
            Content with includes resolved
        """
        # Pattern to match #include directives (including optional trailing semicolon)
        include_pattern = r'#include\s+["<]([^">]+)[">]\s*;?'

        def replace_include(match: re.Match) -> str:
            include_path = match.group(1)
            included_content = self._resolve_include(include_path, base_dir)
            # Add a newline after each include to prevent syntax errors
            return included_content + '\n'

        return re.sub(include_pattern, replace_include, content)

    def _resolve_include(self, include_path: str, base_dir: Path) -> str:
        """
        Resolve an include path and return the processed content.
        
        Args:
            include_path: The include path from the directive
            base_dir: Base directory for relative includes
            
        Returns:
            Processed content of the included file
        """
        # Determine if this is a lygia include
        if include_path.startswith('lygia/'):
            # Lygia library include
            lygia_path = self.lygia_dir / include_path[6:]  # Remove 'lygia/' prefix
            return self._process_file(str(lygia_path))
        else:
            # Relative include
            relative_path = base_dir / include_path
            return self._process_file(str(relative_path))

    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve a file path, checking both shader directory and lygia directory.
        
        Args:
            file_path: Path to resolve
            
        Returns:
            Resolved Path object
        """
        path = Path(file_path)

        # If it's already an absolute path, return as is
        if path.is_absolute():
            return path

        # Check if it's a lygia path
        if file_path.startswith('lygia/'):
            return self.lygia_dir / file_path[6:]

        # Check in shader directory
        shader_path = self.shader_dir / file_path
        if shader_path.exists():
            return shader_path

        # Check in lygia directory
        lygia_path = self.lygia_dir / file_path
        if lygia_path.exists():
            return lygia_path

        # Return the original path (will be checked for existence later)
        return path


# Global pre-processor instance
_shader_preprocessor: Optional[ShaderPreprocessor] = None


def get_shader_preprocessor() -> ShaderPreprocessor:
    """
    Get the global shader pre-processor instance.
    
    Returns:
        ShaderPreprocessor instance
    """
    global _shader_preprocessor
    if _shader_preprocessor is None:
        _shader_preprocessor = ShaderPreprocessor()
    return _shader_preprocessor


def preprocess_shader(shader_path: str) -> str:
    """
    Pre-process a shader file using the global pre-processor.
    
    Args:
        shader_path: Path to the shader file
        
    Returns:
        Pre-processed shader source code
    """
    preprocessor = get_shader_preprocessor()
    return preprocessor.preprocess_shader(shader_path)
