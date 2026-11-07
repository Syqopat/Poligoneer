# Poligoneer

Roblox will not import a mesh with more than 20,000 triangles. Poligoneer takes a model that is over that, cuts it into as few pieces as it can, each one under the limit, and saves them all in one file. Import that file into Studio and the pieces line up exactly where the original was.

I wrote it for character models that come out of AI generators and sculpting tools at 100k triangles and up.

```
$ poligoneer snail.glb
snail.glb -> snail_split.glb  (limit 20,000 triangles per piece)
  Snail     100,488 triangles  6 pieces: 16,748, 16,748, 16,748, 16,748, 16,748, 16,748
100,488 triangles in 6 mesh(es)
```

## What it keeps

The cuts follow the model's shape, so each piece is one solid chunk, not triangles from all over. Shading normals are locked before cutting, which means you won't see a lighting seam where two pieces meet. UVs, materials and textures go with every piece.

Rigged models stay rigged. Every piece keeps the original's vertex groups and armature, so they are all skinned to the same skeleton.

Meshes that are already under the limit are left as they are.

## Setup

You need Python 3.9+ and Blender 4.1+ (I test on 5.2). Poligoneer drives Blender in the background; you never see its window.

```bash
pip install .
```

Or skip installing and run `python -m poligoneer` from this folder.

If Blender is not on your `PATH`, point to it with `--blender` or the `POLIGONEER_BLENDER` environment variable.

## Usage

```bash
poligoneer <model> [-o OUTPUT] [-l LIMIT] [-f {glb,fbx,obj}] [--blender PATH]
```

| Option | Default | |
| --- | --- | --- |
| `model` | | `.glb`, `.gltf`, `.fbx` or `.obj` |
| `-o`, `--output` | `<model>_split.<format>` | where to save the result |
| `-l`, `--limit` | `20000` | most triangles allowed in one piece |
| `-f`, `--format` | same as the input | `glb`, `fbx` or `obj` |
| `--blender` | found automatically | path to Blender |

OBJ can't store a skeleton, so a rigged model saved as OBJ loses its rig. Poligoneer warns you when that happens.

## Into Roblox

Open **Import 3D** in Studio and pick the split file. The importer turns it into one Model with every piece already in place.

## How the cut works

Every face counts as the number of triangles it becomes. Poligoneer sorts the faces along the longest side of the mesh and cuts where the triangle count reaches the right share, then does the same to each half until every piece fits. A 100,000 triangle mesh with a 20,000 limit becomes five pieces, not eight.

## Tests

```bash
python -m unittest discover -s tests -t .
```

Most tests need Blender. They build a plain and a rigged model of about 100k triangles, plus a small one with no stored normals, and check the limit, the triangle count, the bounds, the seams and the rig. Without Blender only the splitting tests run.

## License

MIT. See [LICENSE](LICENSE).
