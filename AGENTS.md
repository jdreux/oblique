# Project Agent Guide for Oblique

Oblique is a minimal, shader‑driven AV synthesizer focused on modularity,
real‑time performance and audio‑reactive visuals. It currently targets macOS on
Apple Silicon; GLSL 330 is required. Design is inspired by ShaderToy and
TouchDesigner while remaining code‑only, extensible and reliability+performance focused.
Follows a stateless, unidirectional data flow fully in code. 

## Repository Structure

- `/core`: engine, renderer and patch definitions
- `/inputs`: audio and other data sources
- `/processing`: signal processing operators
- `/modules`: AV modules pairing Python with GLSL shaders
- `/shaders`: fragment shaders and shared GLSL snippets
- `/projects`: example patches and experiments
- `/external`: third‑party resources

## Architecture

Data flow follows `Input → Processing → AV Module → Output`.
Modules extend `BaseAVModule` and expose metadata:

```python
metadata = {
    "name": "Example",
    "description": "What it does",
    "parameters": {"param": float},
}
```

Module parameters should be defined via dataclasses to provide strongly typed values to
shaders. Prefer adding new modules over modifying the core engine.

## Python Rules

1. Use meaningful names
2. Follow PEP 8 and keep lines ≤100 characters
3. Document modules, classes and functions with docstrings
4. Keep code simple; prefer list comprehensions
5. Use type hints and dataclasses; avoid globals. Strong typing where-ever possible.
6. Handle exceptions with `try`/`except`
7. Use absolute imports and virtual environments. When attempting to run, load venv first. 
8. Write tests and run them. Test your changes by runing `source venv/bin/activate && pytest`
9. Employ strong typing for module/shader interfaces
10. Run command‑line tests with `./start.sh` unless parameters need changes
11. Use `rg` for searches; avoid `grep -R` or `ls -R`

## Shader Conventions

- Shaders start with `#version 330` and a top comment block describing the
  module, author and inputs
- Fragment shader holds most logic; add a vertex shader only if required
- Support optional ping‑pong or off‑screen passes. 

## Performance

- Target 60 FPS at 1080p on Apple Silicon
- Avoid blocking CPU calls and large CPU↔GPU transfers
- Render visuals on the GPU

## AI Agent Support

- Document every parameter and shader uniform
- New modules must include metadata and testable update/render functions
- Prefer declarative, stateless designs with clear type‑safe interfaces

## Testing

Run tests after changes:

```bash
pytest
```

## Pull Requests

- Provide a concise summary of changes
- Report test results in the PR description
