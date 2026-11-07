import json
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from poligoneer.partition import plan_pieces

PIECE_ATTRIBUTE = "poligoneer_piece"


def parse_arguments():
    arguments = sys.argv[sys.argv.index("--") + 1 :]
    input_path, output_path, limit, report_path = arguments
    return Path(input_path), Path(output_path), int(limit), Path(report_path)


def import_model(path):
    suffix = path.suffix.lower()
    if suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        raise ValueError(f"Unsupported input format: {suffix}")


def export_model(path):
    suffix = path.suffix.lower()
    if suffix == ".glb":
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
    elif suffix == ".fbx":
        bpy.ops.export_scene.fbx(filepath=str(path), add_leaf_bones=False, path_mode="COPY", embed_textures=True)
    elif suffix == ".obj":
        bpy.ops.wm.obj_export(filepath=str(path))
    else:
        raise ValueError(f"Unsupported output format: {suffix}")


def remove_bone_shapes():
    shapes = set()
    for armature in (obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"):
        for bone in armature.pose.bones:
            if bone.custom_shape:
                shapes.add(bone.custom_shape)
                bone.custom_shape = None
    for shape in shapes:
        bpy.data.objects.remove(shape, do_unlink=True)
    bpy.context.view_layer.update()


def triangle_count(mesh):
    return sum(len(polygon.vertices) - 2 for polygon in mesh.polygons)


def freeze_normals(mesh):
    mesh.normals_split_custom_set([tuple(normal.vector) for normal in mesh.corner_normals])


def select_only(obj):
    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def separate_piece(obj, piece):
    before = set(bpy.data.objects)
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    edit = bmesh.from_edit_mesh(obj.data)
    layer = edit.faces.layers.int[PIECE_ATTRIBUTE]
    for face in edit.faces:
        face.select_set(face[layer] == piece)
    edit.select_flush_mode()
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    created = [candidate for candidate in bpy.data.objects if candidate not in before]
    return created[0]


def split_object(obj, limit):
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    mesh = obj.data
    weights = [len(polygon.vertices) - 2 for polygon in mesh.polygons]
    centroids = [tuple(polygon.center) for polygon in mesh.polygons]
    pieces = plan_pieces(centroids, weights, limit)
    if len(pieces) <= 1:
        return [obj]

    freeze_normals(mesh)
    assignment = [0] * len(weights)
    for piece_index, piece in enumerate(pieces):
        for face_index in piece:
            assignment[face_index] = piece_index
    attribute = mesh.attributes.new(PIECE_ATTRIBUTE, "INT", "FACE")
    attribute.data.foreach_set("value", assignment)

    base_name = obj.name
    parts = [obj]
    for piece_index in range(1, len(pieces)):
        parts.append(separate_piece(obj, piece_index))

    for number, part in enumerate(parts, 1):
        part.name = f"{base_name}_Part{number}"
        part.data.name = part.name
        part.data.attributes.remove(part.data.attributes[PIECE_ATTRIBUTE])
    return parts


def main():
    input_path, output_path, limit, report_path = parse_arguments()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_model(input_path)
    remove_bone_shapes()

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    report = {"meshes": [], "armatures": sum(1 for obj in bpy.context.scene.objects if obj.type == "ARMATURE")}
    for obj in meshes:
        source_name = obj.name
        source_triangles = triangle_count(obj.data)
        parts = split_object(obj, limit)
        report["meshes"].append(
            {
                "name": source_name,
                "triangles": source_triangles,
                "parts": [{"name": part.name, "triangles": triangle_count(part.data)} for part in parts],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_model(output_path)
    report_path.write_text(json.dumps(report))


main()
