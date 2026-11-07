import json
import sys

import bpy

model_path, report_path = sys.argv[sys.argv.index("--") + 1 :]

bpy.ops.wm.read_factory_settings(use_empty=True)
if model_path.endswith(".obj"):
    bpy.ops.wm.obj_import(filepath=model_path)
else:
    bpy.ops.import_scene.gltf(filepath=model_path)

bone_shapes = {
    bone.custom_shape
    for obj in bpy.context.scene.objects
    if obj.type == "ARMATURE"
    for bone in obj.pose.bones
    if bone.custom_shape
}

normals = []
lows = [float("inf")] * 3
highs = [float("-inf")] * 3
meshes = []
for obj in bpy.context.scene.objects:
    if obj.type != "MESH" or obj in bone_shapes:
        continue
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        for axis in range(3):
            lows[axis] = min(lows[axis], point[axis])
            highs[axis] = max(highs[axis], point[axis])
    rotation = obj.matrix_world.to_3x3()
    for loop in obj.data.loops:
        point = obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
        normal = (rotation @ obj.data.corner_normals[loop.index].vector).normalized()
        normals.append([*point, *normal])
    meshes.append(
        {
            "name": obj.name,
            "triangles": sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons),
            "vertex_groups": sorted(group.name for group in obj.vertex_groups),
            "skinned": any(modifier.type == "ARMATURE" and modifier.object for modifier in obj.modifiers),
            "uv_layers": len(obj.data.uv_layers),
            "materials": len(obj.data.materials),
            "attributes": sorted(attribute.name for attribute in obj.data.attributes),
        }
    )

report = {
    "meshes": meshes,
    "armatures": sum(1 for obj in bpy.context.scene.objects if obj.type == "ARMATURE"),
    "bounds": [lows, highs],
    "normals": normals,
}
with open(report_path, "w") as handle:
    json.dump(report, handle)
