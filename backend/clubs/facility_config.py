"""
Per-facility-type, per-level construction configuration (Phase 3b).

All values are PLACEHOLDERS to be tuned. Format per level:
    upgrade_cost_kc  — cost from the previous level to this one, stored as
                       integer LC (1 KC = 100 LC) like all money game-wide
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
        (2000,   100,   5,  3,  1, False),
        (3000,   500,   8,  7,  1, False),
        (8000,   2000,  15, 14, 2, True),
        (20000,  6000,  30, 28, 3, True),
        (50000,  15000, 60, 42, 5, True),
        (120000, 35000, 120, 63, 8, True),
        (300000, 65000, 250, 84, 12, True),
    ),
    "sports_hall": _levels(
        (4000,   50,    6,  4,  1, False),
        (5000,   300,   10, 7,  1, False),
        (12000,  1000,  18, 14, 2, True),
        (30000,  3000,  35, 28, 3, True),
        (70000,  7000,  70, 42, 5, True),
        (150000, 12000, 130, 63, 8, True),
        (350000, 20000, 260, 84, 12, True),
    ),
    "swimming_pool": _levels(
        (15000,  0,    15, 14, 2, True),
        (10000,  100,  12, 7,  1, False),
        (25000,  500,  25, 21, 3, True),
        (40000,  1500, 40, 28, 3, True),
        (80000,  4000, 70, 42, 5, True),
        (160000, 8000, 130, 63, 8, True),
        (350000, 15000, 240, 84, 12, True),
    ),
    "tennis_court": _levels(
        (1000,   0,    3,  2,  1, False),
        (2000,   50,   5,  4,  1, False),
        (6000,   300,  10, 7,  1, False),
        (15000,  1000, 20, 21, 2, True),
        (40000,  3500, 45, 35, 4, True),
        (100000, 8000, 90, 56, 6, True),
        (250000, 15000, 180, 77, 10, True),
    ),
    "fight_gym": _levels(
        (3000,   0,    4,  3,  1, False),
        (4000,   0,  8,  7,  1, False),
        (10000,   0,  15, 14, 2, True),
        (25000,   0, 30, 21, 3, True),
        (60000,   0, 60, 35, 4, True),
        (140000,   0, 110, 56, 7, True),
        (300000,   0, 220, 77, 10, True),
    ),
    "gym": _levels(
        (5000,   0,    4,  3,  1, False),
        (5000,   0,   6,  5,  1, False),
        (10000,   0,  12, 7,  1, False),
        (20000,   0,  25, 21, 2, True),
        (45000,   0, 45, 35, 4, True),
        (90000,   0, 80, 49, 6, True),
        (180000,   0, 150, 70, 9, True),
    ),
    "medical_center": _levels(
        (8000,   0, 6,  7,  1, False),
        (7000,   0, 8,  7,  1, False),
        (15000,  0, 12, 14, 2, True),
        (30000,  0, 20, 21, 2, True),
        (60000,  0, 30, 28, 3, True),
        (120000, 0, 45, 42, 4, True),
        (250000, 0, 70, 56, 6, True),
    ),
}


# --- recurring staffing (Phase 3d) — required headcount per level 1..7 ---
CLEANERS_REQUIRED = {
    "stadium":        (1, 2, 4, 8, 15, 25, 40),
    "sports_hall":    (1, 2, 4, 7, 12, 18, 28),
    "swimming_pool":  (2, 3, 5, 8, 14, 22, 32),
    "tennis_court":   (1, 1, 2, 4, 8, 14, 22),
    "fight_gym":      (1, 2, 4, 6, 10, 16, 24),
    "gym":            (1, 1, 2, 4, 7, 11, 16),
    "medical_center": (1, 2, 3, 5, 8, 12, 18),
}

MAINTENANCE_REQUIRED = {
    "stadium":        (1, 1, 2, 3, 5, 8, 12),
    "sports_hall":    (1, 1, 2, 3, 5, 7, 10),
    "swimming_pool":  (1, 2, 3, 4, 6, 9, 13),
    "tennis_court":   (1, 1, 1, 2, 3, 5, 8),
    "fight_gym":      (1, 1, 1, 2, 3, 4, 6),
    "gym":            (1, 1, 1, 2, 3, 4, 6),
    "medical_center": (1, 1, 2, 2, 3, 4, 6),
}


def staffing_required(facility_type, level, service_type):
    """Required headcount for 'cleaning' or 'maintenance' at a given level."""
    table = CLEANERS_REQUIRED if service_type == "cleaning" else MAINTENANCE_REQUIRED
    return table[facility_type][level - 1]


def level_config(facility_type, level):
    """Config dict for upgrading TO `level` for a facility type.

    Raises KeyError for unknown types/levels — callers validate first.
    """
    config = dict(LEVEL_CONFIG[facility_type][level])
    config["cleaners_required"] = CLEANERS_REQUIRED[facility_type][level - 1]
    config["maintenance_required"] = MAINTENANCE_REQUIRED[facility_type][level - 1]
    return config
