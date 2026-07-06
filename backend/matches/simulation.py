"""
Phase 2 match simulation engine.
Stats-based, resolves instantly (no real-time streaming yet).
Produces a Fixture result + ordered MatchEvent log.

Design rules from the spec:
- Player stats 1-30 drive attack/defence ratings
- Higher facility level = stat bonus (Level N = +N% to all stats)
- Result is probabilistic but not random noise — a much stronger squad
  should win most of the time
"""

import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from players.models import Player

from .models import Fixture, LeagueStanding, MatchEvent


FOOTBALL_ATTACK_ATTRS  = ["finishing", "dribbling", "off_the_ball", "vision", "passing"]
FOOTBALL_DEFENCE_ATTRS = ["tackling", "marking", "positioning", "strength"]


def _squad_rating(club, attr_list):
    """
    Average of attr_list across the club's current football squad,
    adjusted for the soccer field facility bonus.
    Returns a float 1-30.
    """
    players = list(Player.objects.filter(current_club=club, sport="football"))
    if not players:
        return 5.0   # bare minimum rating if no squad registered

    raw = sum(
        sum(getattr(p, a, 1) for a in attr_list) / len(attr_list)
        for p in players
    ) / len(players)

    facility = club.facilities.filter(facility_type="stadium").first()
    bonus_pct = facility.level if facility else 0
    return raw * (1 + bonus_pct / 100)


def _goal_events(fixture, attacking_club, defending_club, attack_rating, defend_rating, used_minutes):
    """
    Generates a realistic number of goal/miss/save events for one side.
    Returns a list of MatchEvent (unsaved).
    """
    # Expected goals: attack vs defence, scaled to a 0-5 goals range
    advantage = max(0.1, attack_rating / max(defend_rating, 1))
    expected  = min(5, max(0, (advantage - 0.7) * 3))
    goals     = max(0, round(random.gauss(expected, 1)))

    # Chances attempted = goals + misses/saves
    chances = goals + random.randint(1, 4)

    events = []
    for _ in range(chances):
        while True:
            minute = random.randint(1, 90)
            if minute not in used_minutes:
                used_minutes.add(minute)
                break

        if len(events) < goals:
            events.append(MatchEvent(
                fixture=fixture,
                minute=minute,
                event_type=MatchEvent.EventType.GOAL,
                club=attacking_club,
                description=f"Goal for {attacking_club.name}",
            ))
        else:
            # 50/50 miss vs save
            if random.random() < 0.5:
                events.append(MatchEvent(
                    fixture=fixture, minute=minute,
                    event_type=MatchEvent.EventType.MISS,
                    club=attacking_club,
                    description=f"Missed chance for {attacking_club.name}",
                ))
            else:
                events.append(MatchEvent(
                    fixture=fixture, minute=minute,
                    event_type=MatchEvent.EventType.SAVE,
                    club=defending_club,
                    description=f"Save by {defending_club.name}",
                ))
    return events, goals


def _card_events(fixture, home_club, away_club, used_minutes):
    """Sprinkle a few yellow cards and occasionally a red."""
    events = []
    for club in [home_club, away_club]:
        yellows = random.choices([0, 1, 2, 3], weights=[40, 35, 20, 5])[0]
        for _ in range(yellows):
            while True:
                minute = random.randint(1, 90)
                if minute not in used_minutes:
                    used_minutes.add(minute)
                    break
            events.append(MatchEvent(
                fixture=fixture, minute=minute,
                event_type=MatchEvent.EventType.YELLOW,
                club=club,
                description=f"Yellow card for {club.name}",
            ))
        if random.random() < 0.08:   # ~8% chance of a red per team
            while True:
                minute = random.randint(30, 90)
                if minute not in used_minutes:
                    used_minutes.add(minute)
                    break
            events.append(MatchEvent(
                fixture=fixture, minute=minute,
                event_type=MatchEvent.EventType.RED,
                club=club,
                description=f"Red card for {club.name}",
            ))
    return events


@transaction.atomic
def simulate_fixture(fixture: Fixture) -> Fixture:
    """
    Runs the full simulation for one fixture:
    1. Computes squad attack/defence ratings for both sides
    2. Generates goal events
    3. Generates card events
    4. Saves everything and updates league standings
    Returns the updated fixture.
    """
    home, away = fixture.home_club, fixture.away_club

    home_att = _squad_rating(home, FOOTBALL_ATTACK_ATTRS)
    home_def = _squad_rating(home, FOOTBALL_DEFENCE_ATTRS)
    away_att = _squad_rating(away, FOOTBALL_ATTACK_ATTRS)
    away_def = _squad_rating(away, FOOTBALL_DEFENCE_ATTRS)

    # Home advantage: small boost to attack
    home_att *= 1.05

    used_minutes = set()
    home_events, home_goals = _goal_events(fixture, home, away, home_att, away_def, used_minutes)
    away_events, away_goals = _goal_events(fixture, away, home, away_att, home_def, used_minutes)
    card_events             = _card_events(fixture, home, away, used_minutes)

    all_events = sorted(home_events + away_events + card_events, key=lambda e: e.minute)
    MatchEvent.objects.bulk_create(all_events)

    fixture.home_score = home_goals
    fixture.away_score = away_goals
    fixture.status     = Fixture.Status.FINISHED
    fixture.save(update_fields=["home_score", "away_score", "status"])

    _update_standings(fixture)
    return fixture


def _update_standings(fixture: Fixture):
    """Recomputes the LeagueStanding rows for both clubs after a result."""
    for club, scored, conceded in [
        (fixture.home_club, fixture.home_score, fixture.away_score),
        (fixture.away_club, fixture.away_score, fixture.home_score),
    ]:
        standing, _ = LeagueStanding.objects.get_or_create(
            season=fixture.season, club=club
        )
        standing.played += 1
        standing.gf     += scored
        standing.ga     += conceded
        if scored > conceded:
            standing.won    += 1
            standing.points += 3
        elif scored == conceded:
            standing.drawn  += 1
            standing.points += 1
        else:
            standing.lost   += 1
        standing.save()
