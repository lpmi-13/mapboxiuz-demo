"""Tests for the UK coordinate pool."""
import pytest

from api.utils.uk_coordinates import UK_COORDINATES, pick_random_pair


class TestUKCoordinates:
    def test_pool_has_enough_entries(self):
        assert len(UK_COORDINATES) >= 50

    def test_all_entries_have_required_keys(self):
        for entry in UK_COORDINATES:
            assert "name" in entry, f"Missing 'name' in {entry}"
            assert "lat" in entry, f"Missing 'lat' in {entry}"
            assert "lon" in entry, f"Missing 'lon' in {entry}"

    def test_all_coords_are_in_uk_bounding_box(self):
        """Rough bounding box: lat 49–61, lon -8.5–2."""
        for entry in UK_COORDINATES:
            assert 49.0 <= entry["lat"] <= 61.5, f"lat out of range: {entry}"
            assert -9.0 <= entry["lon"] <= 2.5, f"lon out of range: {entry}"

    def test_no_duplicate_names(self):
        names = [e["name"] for e in UK_COORDINATES]
        assert len(names) == len(set(names)), "Duplicate city names found"


class TestPickRandomPair:
    def test_returns_two_distinct_entries(self):
        origin, destination = pick_random_pair()
        assert origin != destination

    def test_both_entries_are_from_pool(self):
        origin, destination = pick_random_pair()
        assert origin in UK_COORDINATES
        assert destination in UK_COORDINATES

    def test_randomness_over_multiple_calls(self):
        # Dicts aren't hashable; compare by name tuples instead
        pairs = {
            (o["name"], d["name"]) for o, d in (pick_random_pair() for _ in range(20))
        }
        # With 100 cities, 20 draws should yield more than 1 unique pair
        assert len(pairs) > 1
