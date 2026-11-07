from math import ceil


class FaceTooLargeError(ValueError):
    pass


def _longest_axis(centroids, indices):
    lows = [float("inf")] * 3
    highs = [float("-inf")] * 3
    for index in indices:
        point = centroids[index]
        for axis in range(3):
            if point[axis] < lows[axis]:
                lows[axis] = point[axis]
            if point[axis] > highs[axis]:
                highs[axis] = point[axis]
    spans = [highs[axis] - lows[axis] for axis in range(3)]
    return spans.index(max(spans))


def _cut_position(ordered, weights, target):
    running = 0
    for position, index in enumerate(ordered):
        if position > 0 and running + weights[index] > target:
            return position
        running += weights[index]
    return len(ordered) - 1


def plan_pieces(centroids, weights, limit):
    if limit < 1:
        raise ValueError("The triangle limit must be at least 1")
    if len(centroids) != len(weights):
        raise ValueError("Every face needs a centroid and a weight")
    for weight in weights:
        if weight > limit:
            raise FaceTooLargeError(f"A single face has {weight} triangles, more than the limit of {limit}")
    if not weights:
        return []

    pieces = []
    pending = [list(range(len(weights)))]
    while pending:
        indices = pending.pop()
        total = sum(weights[index] for index in indices)
        if total <= limit:
            pieces.append(indices)
            continue

        count = ceil(total / limit)
        axis = _longest_axis(centroids, indices)
        ordered = sorted(indices, key=lambda index: (centroids[index][axis], index))
        cut = _cut_position(ordered, weights, total * (count // 2) / count)
        pending.append(ordered[cut:])
        pending.append(ordered[:cut])

    return pieces


def triangles_in(pieces, weights):
    return [sum(weights[index] for index in piece) for piece in pieces]
