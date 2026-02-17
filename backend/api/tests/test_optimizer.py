"""Tests for the TSP solver."""
import pytest

from api.services.optimizer import (
    _route_cost,
    brute_force_tsp,
    nearest_neighbour_tsp,
    solve_tsp,
    two_opt,
)

# Simple 4-city distance matrix: optimal tour 0→1→3→2→(0) cost = 1+1+1+1 = 4
#
#      0  1  2  3
#  0 [ 0, 1, 4, 2 ]
#  1 [ 1, 0, 3, 1 ]
#  2 [ 4, 3, 0, 1 ]
#  3 [ 2, 1, 1, 0 ]
MATRIX_4 = [
    [0, 1, 4, 2],
    [1, 0, 3, 1],
    [4, 3, 0, 1],
    [2, 1, 1, 0],
]
# Optimal (non-round) order anchored at 0: 0 → 1 → 3 → 2  (cost 1+1+1=3)
# or equivalently 0 → 2 → 3 → 1  (cost 4+1+1=6)  — so 0,1,3,2 is better


class TestRouteCost:
    def test_simple_cost(self):
        matrix = [[0, 2], [2, 0]]
        assert _route_cost([0, 1], matrix) == 2

    def test_three_stops(self):
        # 0→1 cost 1, 1→2 cost 3 → total 4
        matrix = [[0, 1, 9], [1, 0, 3], [9, 3, 0]]
        assert _route_cost([0, 1, 2], matrix) == 4


class TestBruteForceTSP:
    def test_returns_all_stops(self):
        order = brute_force_tsp(MATRIX_4)
        assert sorted(order) == [0, 1, 2, 3]

    def test_starts_at_zero(self):
        order = brute_force_tsp(MATRIX_4)
        assert order[0] == 0

    def test_finds_optimal_order(self):
        order = brute_force_tsp(MATRIX_4)
        best_cost = _route_cost(order, MATRIX_4)
        # Brute force must beat or equal every other permutation
        import itertools

        for perm in itertools.permutations([0, 1, 2, 3]):
            if perm[0] != 0:
                continue
            assert best_cost <= _route_cost(list(perm), MATRIX_4)

    def test_single_permutation_two_stops(self):
        m = [[0, 5], [5, 0]]
        order = brute_force_tsp(m)
        assert order == [0, 1]


class TestNearestNeighbourTSP:
    def test_returns_all_stops(self):
        order = nearest_neighbour_tsp(MATRIX_4)
        assert sorted(order) == [0, 1, 2, 3]

    def test_starts_at_zero(self):
        order = nearest_neighbour_tsp(MATRIX_4)
        assert order[0] == 0

    def test_greedy_picks_nearest(self):
        # From 0 the nearest is 1 (cost 1), from 1 nearest unvisited is 3 (cost 1)
        order = nearest_neighbour_tsp(MATRIX_4)
        assert order[:3] == [0, 1, 3]


class TestTwoOpt:
    def test_does_not_worsen_solution(self):
        initial = [0, 2, 1, 3]
        improved = two_opt(initial, MATRIX_4)
        assert _route_cost(improved, MATRIX_4) <= _route_cost(initial, MATRIX_4)

    def test_preserves_all_stops(self):
        initial = [0, 2, 1, 3]
        improved = two_opt(initial, MATRIX_4)
        assert sorted(improved) == [0, 1, 2, 3]


class TestSolveTSP:
    def test_small_uses_brute_force_result(self):
        order = solve_tsp(MATRIX_4)
        assert sorted(order) == [0, 1, 2, 3]

    def test_round_trip_appends_start(self):
        order = solve_tsp(MATRIX_4, round_trip=True)
        assert order[0] == order[-1]
        assert len(order) == 5

    def test_single_stop_returns_immediately(self):
        m = [[0]]
        order = solve_tsp(m)
        assert order == [0]

    def test_two_stops_trivial(self):
        m = [[0, 1], [1, 0]]
        order = solve_tsp(m)
        assert sorted(order) == [0, 1]

    def test_large_uses_heuristic(self):
        """For >12 stops the solver should still return a valid tour."""
        n = 15
        # Identity matrix with unit off-diagonals
        matrix = [[0 if i == j else 1 for j in range(n)] for i in range(n)]
        order = solve_tsp(matrix)
        assert sorted(order) == list(range(n))
