import random
import unittest
from math import ceil

from poligoneer.partition import FaceTooLargeError, plan_pieces, triangles_in


def grid(columns, rows, weight=2):
    centroids = [(float(x), float(y), 0.0) for y in range(rows) for x in range(columns)]
    return centroids, [weight] * len(centroids)


class PlanPiecesTest(unittest.TestCase):
    def test_a_mesh_under_the_limit_stays_whole(self):
        centroids, weights = grid(10, 10)
        pieces = plan_pieces(centroids, weights, 1000)
        self.assertEqual(len(pieces), 1)
        self.assertEqual(sorted(pieces[0]), list(range(100)))

    def test_every_piece_respects_the_limit(self):
        centroids, weights = grid(200, 250)
        pieces = plan_pieces(centroids, weights, 20000)
        self.assertTrue(all(count <= 20000 for count in triangles_in(pieces, weights)))

    def test_a_uniform_mesh_uses_the_fewest_pieces(self):
        centroids, weights = grid(200, 250)
        pieces = plan_pieces(centroids, weights, 20000)
        self.assertEqual(len(pieces), ceil(sum(weights) / 20000))

    def test_every_face_lands_in_exactly_one_piece(self):
        rng = random.Random(7)
        centroids = [(rng.random(), rng.random(), rng.random()) for _ in range(5000)]
        weights = [rng.choice([1, 2, 3]) for _ in centroids]
        pieces = plan_pieces(centroids, weights, 700)
        assigned = sorted(index for piece in pieces for index in piece)
        self.assertEqual(assigned, list(range(len(centroids))))
        self.assertTrue(all(count <= 700 for count in triangles_in(pieces, weights)))

    def test_pieces_are_spatially_separate_along_the_longest_axis(self):
        centroids, weights = grid(100, 2)
        pieces = plan_pieces(centroids, weights, 200)
        spans = sorted((min(centroids[i][0] for i in piece), max(centroids[i][0] for i in piece)) for piece in pieces)
        for (_, previous_high), (next_low, _) in zip(spans, spans[1:]):
            self.assertLess(previous_high, next_low)

    def test_the_plan_is_deterministic(self):
        rng = random.Random(3)
        centroids = [(rng.random(), rng.random(), rng.random()) for _ in range(2000)]
        weights = [2] * len(centroids)
        self.assertEqual(plan_pieces(centroids, weights, 500), plan_pieces(centroids, weights, 500))

    def test_a_face_above_the_limit_is_refused(self):
        with self.assertRaises(FaceTooLargeError):
            plan_pieces([(0.0, 0.0, 0.0)], [30], 20)

    def test_an_empty_mesh_has_no_pieces(self):
        self.assertEqual(plan_pieces([], [], 100), [])

    def test_invalid_limits_are_refused(self):
        with self.assertRaises(ValueError):
            plan_pieces([(0.0, 0.0, 0.0)], [1], 0)


if __name__ == "__main__":
    unittest.main()
