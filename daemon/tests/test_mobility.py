import pytest

from core.location.mobility import WayPoint


class TestMobility:
    @pytest.mark.parametrize(
        "wp1, wp2, expected",
        [
            (WayPoint(10.0, 1, [0, 0], 1.0), WayPoint(1.0, 2, [0, 0], 1.0), False),
            (WayPoint(1.0, 1, [0, 0], 1.0), WayPoint(10.0, 2, [0, 0], 1.0), True),
            (WayPoint(1.0, 1, [0, 0], 1.0), WayPoint(1.0, 2, [0, 0], 1.0), True),
            (WayPoint(1.0, 2, [0, 0], 1.0), WayPoint(1.0, 1, [0, 0], 1.0), False),
        ],
    )
    def test_waypoint_lessthan(self, wp1, wp2, expected):
        assert (wp1 < wp2) == expected
