import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from math import ceil
from pathlib import Path

from poligoneer.cli import PoligoneerError, find_blender, main

SCRIPTS = Path(__file__).resolve().parent / "blender"
LIMIT = 20000

try:
    BLENDER = find_blender(None)
except PoligoneerError:
    BLENDER = None


def run_script(script, *arguments):
    subprocess.run(
        [BLENDER, "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(SCRIPTS / script), "--", *arguments],
        check=True,
        capture_output=True,
    )


def cell(point):
    return tuple(round(value * 1000) for value in point)


def seam_mismatches(before, after):
    grid = {}
    for sample in before:
        grid.setdefault(cell(sample[:3]), []).append(sample)
    mismatches = 0
    for sample in after:
        x, y, z = cell(sample[:3])
        neighbours = (
            candidate
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            for dz in (-1, 0, 1)
            for candidate in grid.get((x + dx, y + dy, z + dz), ())
        )
        if not any(
            sum((a - b) ** 2 for a, b in zip(sample[:3], candidate[:3])) < 1e-8
            and sum(a * b for a, b in zip(sample[3:], candidate[3:])) > 0.999
            for candidate in neighbours
        ):
            mismatches += 1
    return mismatches


def inspect(model, workspace):
    report = Path(workspace) / f"{Path(model).stem}.json"
    run_script("inspect_model.py", str(model), str(report))
    return json.loads(report.read_text())


@unittest.skipUnless(BLENDER, "Blender is not installed")
class SplitModelTest(unittest.TestCase):
    def split(self, kind, source_format="glb", limit=LIMIT):
        directory = tempfile.TemporaryDirectory(prefix="poligoneer-test-")
        self.addCleanup(directory.cleanup)
        workspace = directory.name
        source = Path(workspace) / f"{kind}.{source_format}"
        output = Path(workspace) / f"{kind}_split.glb"
        run_script("make_fixture.py", str(source), kind)
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = main([str(source), "-o", str(output), "--limit", str(limit)])
        self.assertEqual(exit_code, 0)
        return inspect(source, workspace), inspect(output, workspace)

    def assert_reassembles(self, before, after, materials=1, limit=LIMIT):
        original = before["meshes"][0]["triangles"]
        self.assertGreater(original, limit)
        self.assertEqual(len(after["meshes"]), ceil(original / limit))
        self.assertEqual(sum(mesh["triangles"] for mesh in after["meshes"]), original)
        for mesh in after["meshes"]:
            self.assertLessEqual(mesh["triangles"], limit)
            self.assertEqual(mesh["uv_layers"], before["meshes"][0]["uv_layers"])
            self.assertEqual(mesh["materials"], materials)
            self.assertNotIn("poligoneer_piece", mesh["attributes"])
        self.assertEqual(seam_mismatches(before["normals"], after["normals"]), 0, "shading must not change where pieces meet")
        for bound_before, bound_after in zip(before["bounds"], after["bounds"]):
            for axis in range(3):
                self.assertAlmostEqual(bound_before[axis], bound_after[axis], places=4)

    def test_a_static_model_is_split_under_the_limit_and_keeps_its_shape(self):
        before, after = self.split("static")
        self.assert_reassembles(before, after)
        self.assertEqual(after["armatures"], 0)

    def test_a_model_without_stored_normals_has_no_seams(self):
        before, after = self.split("coarse", "obj", limit=200)
        self.assert_reassembles(before, after, materials=0, limit=200)

    def test_a_rigged_model_keeps_its_skeleton_in_every_piece(self):
        before, after = self.split("rigged")
        self.assert_reassembles(before, after)
        self.assertEqual(after["armatures"], 1)
        for mesh in after["meshes"]:
            self.assertTrue(mesh["skinned"], mesh["name"])
            self.assertTrue(set(mesh["vertex_groups"]) <= {"Lower", "Upper"})
            self.assertTrue(mesh["vertex_groups"])


@unittest.skipUnless(BLENDER, "Blender is not installed")
class CommandLineTest(unittest.TestCase):
    def test_a_missing_input_is_reported(self):
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main(["missing.glb"]), 1)
        self.assertIn("not found", errors.getvalue())

    def test_an_output_with_the_wrong_format_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".glb") as source, contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main([source.name, "-o", "out.fbx", "-f", "glb"]), 1)
        self.assertIn("--format", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
