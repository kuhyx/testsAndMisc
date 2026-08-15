"""Route (d) 3D: a Blender scene script, run headless.

This module is *emitted* and executed by ``blender --background --python``, so
it must not import anything from this package -- the Blender interpreter has
no path to it. It is kept here as a data file rather than a library so the
repo's linters still see it as Python.

The 3D cell exists to answer one question: does a rendered mesh, put through
the same finishing stage as the vector route, clear the pixel gates? The
render is continuous-tone by nature, so the expectation is the same as every
other continuous route -- it needs the finisher.
"""

from __future__ import annotations

from typing import Final

# Rendered square edge length before downscaling. Kept small: the finisher
# reduces to 32px anyway, and Cycles time scales with pixel count.
RENDER_SIZE: Final = 256

# Executed inside Blender's own Python. Written as a template rather than
# imported, because Blender cannot see this package.
SCENE_TEMPLATE: Final = """
import sys
import bpy
import mathutils

SUBJECT = sys.argv[-2]
OUT = sys.argv[-1]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = {size}
scene.render.resolution_y = {size}
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = OUT


def material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = 0.45
    return mat


GOLD = (0.84, 0.64, 0.24, 1.0)
CYAN = (0.36, 0.69, 0.75, 1.0)
RED = (0.69, 0.24, 0.24, 1.0)
BONE = (0.78, 0.73, 0.67, 1.0)


def add(obj, rgba):
    obj.data.materials.append(material(obj.name, rgba))
    return obj


def build_coin():
    bpy.ops.mesh.primitive_cylinder_add(radius=1.1, depth=0.16, vertices=48)
    add(bpy.context.object, GOLD)
    bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.08)
    add(bpy.context.object, GOLD)


def build_gem():
    bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=1.2, vertices=8)
    add(bpy.context.object, CYAN)
    bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=0.7, vertices=8)
    bpy.context.object.rotation_euler = (3.14159, 0, 0)
    bpy.context.object.location = (0, 0, 0.95)
    add(bpy.context.object, CYAN)


def build_ring():
    bpy.ops.mesh.primitive_torus_add(major_radius=0.85, minor_radius=0.16)
    add(bpy.context.object, GOLD)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=0.34, subdivisions=1)
    bpy.context.object.location = (0, 0, 0.95)
    add(bpy.context.object, CYAN)


def build_bone():
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.8, vertices=16)
    add(bpy.context.object, BONE)
    for z in (0.9, -0.9):
        for x in (-0.22, 0.22):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.34, segments=16)
            bpy.context.object.location = (x, 0, z)
            add(bpy.context.object, BONE)


def build_bomb():
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=32)
    add(bpy.context.object, (0.16, 0.15, 0.17, 1.0))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.6, vertices=12)
    bpy.context.object.location = (0.25, 0, 1.15)
    add(bpy.context.object, RED)


BUILDERS = {{
    "coin": build_coin,
    "gem": build_gem,
    "ring": build_ring,
    "bone": build_bone,
    "bomb": build_bomb,
}}

BUILDERS[SUBJECT]()

bpy.ops.object.camera_add(location=(0, -4.2, 2.6))
camera = bpy.context.object
camera.rotation_euler = mathutils.Euler((1.02, 0, 0))
camera.data.type = "ORTHO"
camera.data.ortho_scale = 3.0
scene.camera = camera

bpy.ops.object.light_add(type="SUN", location=(2.5, -3.0, 5.0))
bpy.context.object.data.energy = 4.0
bpy.ops.object.light_add(type="AREA", location=(-3.0, -2.0, 2.0))
bpy.context.object.data.energy = 90.0

bpy.ops.render.render(write_still=True)
"""


def scene_script(size: int = RENDER_SIZE) -> str:
    """Return the Blender scene script for a given render size.

    Args:
        size: Square render edge length in pixels.

    Returns:
        Python source to hand to ``blender --python``.
    """
    return SCENE_TEMPLATE.format(size=size)


# Subjects with a 3D build. Deliberately a subset: a mesh for "scroll" or
# "meat" would be modelling work, not a route comparison, and the cell's
# purpose is to test whether render->finish clears the gates at all.
SUBJECTS_3D: Final = ("coin", "gem", "ring", "bone", "bomb")
