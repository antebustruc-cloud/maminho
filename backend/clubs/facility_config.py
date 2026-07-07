"""
Per-facility-type, per-level construction configuration (Phase 3b).

All values are PLACEHOLDERS to be tuned. Format per level:
    upgrade_cost_kc  — KC cost from the previous level to this one
    capacity         — seats (0 = no spectator capacity)
    required_workers — construction workers needed (recorded only for now;
                       companies/hiring are a later phase)
    build_time_days  — real-world days the project takes
    required_guards  — security guards during construction (recorded only)
    is_major         — major works make the facility unusable while running;
                       minor works don't

Kept as plain data (not DB rows) so it's easy to tune in one place and
ships with the code, mirroring COSTS / LICENSE_COSTS from earlier phases.
"""

MAX_LEVEL = 7

_FIELDS = ("upgrade_cost_kc", "capacity", "required_workers",
           "build_time_days", "required_guards", "is_major")


def _levels(*rows):
    """rows of (cost, capacity, workers, days, guards, is_major) → {level: {...}}"""
    return {
        level: dict(zip(_FIELDS, row))
        for level, row in enumerate(rows, start=1)
    }


LEVEL_CONFIG = {
    "stadium": _levels(
        (20,   100,   5,  3,  1, False),
        (30,   500,   8,  7,  1, False),
        (80,   2000,  15, 14, 2, True),
        (200,  6000,  30, 28, 3, True),
        (500,  15000, 60, 42, 5, True),
        (1200, 35000, 120, 63, 8, True),
        (3000, 65000, 250, 84, 12, True),
    ),
    "sports_hall": _levels(
        (40,   50,    6,  4,  1, False),
        (50,   300,   10, 7,  1, False),
        (120,  1000,  18, 14, 2, True),
        (300,  3000,  35, 28, 3, True),
        (700,  7000,  70, 42, 5, True),
        (1500, 12000, 130, 63, 8, True),
        (3500, 20000, 260, 84, 12, True),
    ),
    "swimming_pool": _levels(
        (150,  0,    15, 14, 2, True),
        (100,  100,  12, 7,  1, False),
        (250,  500,  25, 21, 3, True),
        (400,  1500, 40, 28, 3, True),
        (800,  4000, 70, 42, 5, True),
        (1600, 8000, 130, 63, 8, True),
        (3500, 15000, 240, 84, 12, True),
    ),
    "tennis_court": _levels(
        (10,   0,    3,  2,  1, False),
        (20,   50,   5,  4,  1, False),
        (60,   300,  10, 7,  1, False),
        (150,  1000, 20, 21, 2, True),
        (400,  3500, 45, 35, 4, True),
        (1000, 8000, 90, 56, 6, True),
        (2500, 15000, 180, 77, 10, True),
    ),
    "fight_gym": _levels(
        (30,   0,    4,  3,  1, False),
        (40,   100,  8,  7,  1, False),
        (100,  500,  15, 14, 2, True),
        (250,  1500, 30, 21, 3, True),
        (600,  4000, 60, 35, 4, True),
        (1400, 9000, 110, 56, 7, True),
        (3000, 18000, 220, 77, 10, True),
    ),
    "gym": _levels(
        (50,  0,    4,  3,  1, False),
        (50,  50,   6,  5,  1, False),
        (100, 200,  12, 7,  1, False),
        (200, 600,  25, 21, 2, True),
        (450, 1500, 45, 35, 4, True),
        (900, 3000, 80, 49, 6, True),
        (1800, 6000, 150, 70, 9, True),
    ),
    "medical_center": _levels(
        (80,   0, 6,  7,  1, False),
        (70,   0, 8,  7,  1, False),
        (150,  0, 12, 14, 2, True),
        (300,  0, 20, 21, 2, True),
        (600,  0, 30, 28, 3, True),
        (1200, 0, 45, 42, 4, True),
        (2500, 0, 70, 56, 6, True),
    ),
}


def level_config(facility_type, level):
    """Config dict for upgrading TO `level` for a facility type.

    Raises KeyError for unknown types/levels — callers validate first.
    """
    return LEVEL_CONFIG[facility_type][level]
