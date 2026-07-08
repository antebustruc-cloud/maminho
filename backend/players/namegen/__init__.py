"""
Weighted per-country name generation (Phase 3d). Adding a country =
adding one module next to hr.py exposing FIRST_NAMES and LAST_NAMES as
lists of (name, weight) tuples, then registering it in COUNTRIES.
Duplicates across generated players are allowed by design.
"""

import random

from . import hr

COUNTRIES = {
    "HR": hr,
}

DEFAULT_COUNTRY = "HR"


def generate_name(country=DEFAULT_COUNTRY):
    """A weighted 'First Last' name for the given ISO country code."""
    pool = COUNTRIES.get(country, COUNTRIES[DEFAULT_COUNTRY])
    first = random.choices([n for n, _ in pool.FIRST_NAMES],
                           weights=[w for _, w in pool.FIRST_NAMES])[0]
    last = random.choices([n for n, _ in pool.LAST_NAMES],
                          weights=[w for _, w in pool.LAST_NAMES])[0]
    return f"{first} {last}"


def supported_countries():
    return sorted(COUNTRIES.keys())
