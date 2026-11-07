import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from poligoneer import __version__

ROBLOX_TRIANGLE_LIMIT = 20000
INPUT_FORMATS = (".glb", ".gltf", ".fbx", ".obj")
OUTPUT_FORMATS = ("glb", "fbx", "obj")
BLENDER_ENVIRONMENT_VARIABLE = "POLIGONEER_BLENDER"
JOB_PATH = Path(__file__).resolve().parent / "blender_job.py"
COMMON_BLENDER_PATHS = (
    "/Applications/Blender.app/Contents/MacOS/Blender",
    r"C:\Program Files\Blender Foundation\Blender\blender.exe",
)


class PoligoneerError(Exception):
    pass


def find_blender(explicit):
    candidates = [explicit, os.environ.get(BLENDER_ENVIRONMENT_VARIABLE), shutil.which("blender"), *COMMON_BLENDER_PATHS]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise PoligoneerError(
        f"Blender was not found. Pass --blender PATH or set {BLENDER_ENVIRONMENT_VARIABLE}."
    )


def resolve_output(input_path, output, output_format):
    if output:
        path = Path(output)
        suffix = path.suffix.lower().lstrip(".")
        if output_format and suffix != output_format:
            raise PoligoneerError(f"The output file ends in .{suffix} but --format is {output_format}")
        if suffix not in OUTPUT_FORMATS:
            raise PoligoneerError(f"Unsupported output format: .{suffix}")
        return path
    chosen = output_format or ("glb" if input_path.suffix.lower() == ".gltf" else input_path.suffix.lower().lstrip("."))
    return input_path.with_name(f"{input_path.stem}_split.{chosen}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="poligoneer",
        description="Split high-poly models into pieces under a triangle limit that reassemble in place.",
    )
    parser.add_argument("input", help="model to split (.glb, .gltf, .fbx, .obj)")
    parser.add_argument("-o", "--output", help="output file (default: <input>_split.<format>)")
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=ROBLOX_TRIANGLE_LIMIT,
        help=f"maximum triangles per piece (default: {ROBLOX_TRIANGLE_LIMIT}, the Roblox MeshPart limit)",
    )
    parser.add_argument("-f", "--format", choices=OUTPUT_FORMATS, help="output format (default: same as input)")
    parser.add_argument("--blender", help=f"path to the Blender executable (or set {BLENDER_ENVIRONMENT_VARIABLE})")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def run_job(blender, input_path, output_path, limit):
    with tempfile.TemporaryDirectory(prefix="poligoneer-") as workspace:
        report_path = Path(workspace) / "report.json"
        command = [
            blender,
            "--background",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(JOB_PATH),
            "--",
            str(input_path),
            str(output_path),
            str(limit),
            str(report_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0 or not report_path.is_file():
            details = "\n".join((result.stdout + result.stderr).strip().splitlines()[-15:])
            raise PoligoneerError(f"Blender could not split the model:\n{details}")
        return json.loads(report_path.read_text())


def print_report(report, input_path, output_path, limit):
    print(f"{input_path.name} -> {output_path}  (limit {limit:,} triangles per piece)")
    width = max((len(mesh["name"]) for mesh in report["meshes"]), default=4)
    total_triangles = 0
    total_parts = 0
    for mesh in report["meshes"]:
        parts = mesh["parts"]
        counts = ", ".join(f"{part['triangles']:,}" for part in parts)
        label = "kept whole" if len(parts) == 1 else f"{len(parts)} pieces: {counts}"
        print(f"  {mesh['name']:<{width}}  {mesh['triangles']:>9,} triangles  {label}")
        total_triangles += mesh["triangles"]
        total_parts += len(parts)
    print(f"{total_triangles:,} triangles in {total_parts} mesh(es)")


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    try:
        input_path = Path(arguments.input)
        if not input_path.is_file():
            raise PoligoneerError(f"Input file not found: {input_path}")
        if input_path.suffix.lower() not in INPUT_FORMATS:
            raise PoligoneerError(f"Unsupported input format: {input_path.suffix}")
        if arguments.limit < 1:
            raise PoligoneerError("The limit must be at least 1 triangle")
        output_path = resolve_output(input_path, arguments.output, arguments.format)
        if output_path.resolve() == input_path.resolve():
            raise PoligoneerError("The output would overwrite the input")

        report = run_job(find_blender(arguments.blender), input_path, output_path, arguments.limit)
        print_report(report, input_path, output_path, arguments.limit)
        if report["armatures"] and output_path.suffix.lower() == ".obj":
            print("Warning: OBJ files cannot hold a rig; the skeleton and weights were not written.", file=sys.stderr)
        return 0
    except PoligoneerError as error:
        print(f"poligoneer: {error}", file=sys.stderr)
        return 1
