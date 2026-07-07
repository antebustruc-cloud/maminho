"""
Fixture generation (Phase 3b): double round-robin schedule built ONLY from
clubs registered for the season (SeasonRegistration). Unregistered clubs
are excluded from fixtures — and therefore from standings, which are only
created during simulation for clubs that play.

Team sports only; individual-sport event formats are a later phase.
"""

from datetime import timedelta

from django.utils import timezone

from clubs.models import SeasonRegistration, SportLicense

from .models import Fixture


def generate_round_robin_fixtures(season):
    """
    Create home-and-away round-robin fixtures for `season` from its
    registered clubs. Returns the number of fixtures created.

    Raises ValueError if the sport isn't a team sport, fewer than two
    clubs are registered, or fixtures already exist for the season.
    """
    if SportLicense.category_for(season.sport) != SportLicense.SportCategory.TEAM:
        raise ValueError(f"{season.sport} is not a team sport — no league fixtures.")
    if season.fixtures.exists():
        raise ValueError("Season already has fixtures.")

    clubs = [r.club for r in
             SeasonRegistration.objects.filter(season=season).select_related("club")]
    if len(clubs) < 2:
        raise ValueError("Need at least two registered clubs to generate fixtures.")

    # Circle method: rotate all but the first club. Odd club count gets a
    # bye (None) each round.
    table = list(clubs)
    if len(table) % 2:
        table.append(None)
    n = len(table)
    rounds = []
    for _ in range(n - 1):
        pairs = [(table[i], table[n - 1 - i]) for i in range(n // 2)]
        rounds.append([(h, a) for h, a in pairs if h is not None and a is not None])
        table = [table[0]] + [table[-1]] + table[1:-1]

    # Second leg with home/away swapped.
    rounds += [[(a, h) for h, a in rnd] for rnd in rounds]

    # Spread rounds evenly across the season dates (one round per matchday).
    start = timezone.make_aware(
        timezone.datetime.combine(season.start_date, timezone.datetime.min.time())
    ) + timedelta(hours=18)
    total_days = max((season.end_date - season.start_date).days, 1)
    gap = max(total_days // max(len(rounds), 1), 1)

    created = 0
    for round_no, rnd in enumerate(rounds):
        matchday = start + timedelta(days=round_no * gap)
        for home, away in rnd:
            Fixture.objects.create(
                season=season, home_club=home, away_club=away,
                scheduled_at=matchday,
            )
            created += 1
    return created
