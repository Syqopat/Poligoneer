import sys

import bpy

output_path, kind = sys.argv[sys.argv.index("--") + 1 :]

bpy.ops.wm.read_factory_settings(use_empty=True)
segments, rings = (32, 16) if kind == "coarse" else (316, 160)
bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=2, calc_uvs=True)
sphere = bpy.context.active_object
sphere.name = "Snail"
bpy.ops.object.shade_smooth()

material = bpy.data.materials.new("Shell")
material.diffuse_color = (0.55, 0.35, 0.2, 1.0)
sphere.data.materials.append(material)

if kind == "rigged":
    armature_data = bpy.data.armatures.new("Rig")
    armature = bpy.data.objects.new("Rig", armature_data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    lower = armature_data.edit_bones.new("Lower")
    lower.head, lower.tail = (0, 0, -2), (0, 0, 0)
    upper = armature_data.edit_bones.new("Upper")
    upper.head, upper.tail = (0, 0, 0), (0, 0, 2)
    upper.parent = lower
    bpy.ops.object.mode_set(mode="OBJECT")

    lower_group = sphere.vertex_groups.new(name="Lower")
    upper_group = sphere.vertex_groups.new(name="Upper")
    for vertex in sphere.data.vertices:
        group = upper_group if vertex.co.z > 0 else lower_group
        group.add([vertex.index], 1.0, "REPLACE")
    modifier = sphere.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    sphere.parent = armature

if output_path.endswith(".obj"):
    bpy.ops.wm.obj_export(filepath=output_path, export_normals=False, export_smooth_groups=True, export_materials=False)
else:
    bpy.ops.export_scene.gltf(filepath=output_path, export_format="GLB")
