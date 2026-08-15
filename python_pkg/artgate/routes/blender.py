"""Route (d) 3D: drive Blender headless and render one subject.

Blender runs as a subprocess with its own interpreter, so the scene is passed
as a generated script file rather than imported. Failures are surfaced as
exceptions -- a missing Blender or a non-zero exit is reported, never silently
skipped, because a quietly-absent route would show up in the decision table as
a legitimate zero.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from python_pkg.artgate.routes.blender_scene import (
    RENDER_SIZE,
    SUBJECTS_3D,
    scene_script,
)

# Blender can take a while on first run (shader compilation); give it room.
RENDER_TIMEOUT_S = 300


class BlenderError(RuntimeError):
    """Raised when Blender is unavailable or the render fails."""


def render(name: str, out: Path, size: int = RENDER_SIZE) -> Path:
    """Render one 3D subject to a transparent PNG.

    Args:
        name: One of :data:`SUBJECTS_3D`.
        out: Destination PNG path.
        size: Square render edge length.

    Returns:
        The written path.

    Raises:
        KeyError: If the subject has no 3D build.
        BlenderError: If Blender is missing, times out, or exits non-zero.
    """
    if name not in SUBJECTS_3D:
        msg = f"no 3D scene for {name!r}"
        raise KeyError(msg)
    binary = shutil.which("blender")
    if binary is None:
        msg = "blender is not installed"
        raise BlenderError(msg)

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(scene_script(size))
        script = Path(handle.name)

    try:
        result = subprocess.run(
            [
                binary,
                "--background",
                "--factory-startup",
                "--python",
                str(script),
                "--",
                name,
                str(out.with_suffix("")),
            ],
            capture_output=True,
            check=False,
            timeout=RENDER_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        msg = f"blender timed out rendering {name}"
        raise BlenderError(msg) from exc
    finally:
        script.unlink(missing_ok=True)

    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace")[-400:]
        msg = f"blender failed for {name}: {detail}"
        raise BlenderError(msg)

    # Blender exits 0 even when the embedded script raises -- measured against
    # 5.2, where a bad render-engine enum produced a clean exit and no file.
    # Trusting the return code alone would report a phantom success.
    if not out.exists():
        detail = result.stderr.decode(errors="replace")[-400:]
        msg = f"blender wrote no file for {name} despite exit 0: {detail}"
        raise BlenderError(msg)
    return out
