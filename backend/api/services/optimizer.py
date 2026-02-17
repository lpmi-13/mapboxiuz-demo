"""TSP solvers: brute-force for ≤12 stops, nearest-neighbour + 2-opt for more."""
import itertools


def _route_cost(order: list[int], matrix: list[list[float]]) -> float:
    return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def brute_force_tsp(
    matrix: list[list[float]], fixed_start: bool = False
) -> list[int]:
    """
    Try every permutation and return the order with the lowest total distance.

    When fixed_start is True the first stop is kept in position 0.
    Fixing index 0 is always done to avoid evaluating rotational duplicates.
    """
    n = len(matrix)
    indices = list(range(n))
    inner = indices[1:]  # always fix index 0 as anchor

    best_order: list[int] = []
    best_cost = float("inf")

    for perm in itertools.permutations(inner):
        order = [0] + list(perm)
        cost = _route_cost(order, matrix)
        if cost < best_cost:
            best_cost = cost
            best_order = order

    return best_order


def nearest_neighbour_tsp(
    matrix: list[list[float]], fixed_start: bool = False
) -> list[int]:
    """Greedy nearest-neighbour heuristic."""
    n = len(matrix)
    unvisited = set(range(n))
    start = 0
    unvisited.remove(start)
    order = [start]

    while unvisited:
        current = order[-1]
        nearest = min(unvisited, key=lambda j: matrix[current][j])
        order.append(nearest)
        unvisited.remove(nearest)

    return order


def two_opt(order: list[int], matrix: list[list[float]]) -> list[int]:
    """2-opt local-search improvement over a nearest-neighbour solution."""
    n = len(order)
    best = order[:]
    improved = True

    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                if _route_cost(candidate, matrix) < _route_cost(best, matrix):
                    best = candidate
                    improved = True

    return best


def solve_tsp(
    matrix: list[list[float]],
    fixed_start: bool = False,
    round_trip: bool = False,
) -> list[int]:
    """
    Choose solver based on problem size and return the stop visit order.

    - ≤ 12 stops → brute-force (exact)
    - > 12 stops → nearest-neighbour + 2-opt (heuristic)

    When round_trip is True the starting stop is appended at the end.
    """
    n = len(matrix)
    if n < 2:
        return list(range(n))

    if n <= 12:
        order = brute_force_tsp(matrix, fixed_start)
    else:
        order = nearest_neighbour_tsp(matrix, fixed_start)
        order = two_opt(order, matrix)

    if round_trip:
        order = order + [order[0]]

    return order
