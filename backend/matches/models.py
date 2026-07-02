from django.db import models

from clubs.models import Club, Season


class Fixture(models.Model):
    """A scheduled match between two clubs in a season."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        FINISHED  = "finished",  "Finished"

    season     = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="fixtures")
    home_club  = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="home_fixtures")
    away_club  = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="away_fixtures")
    scheduled_at = models.DateTimeField()
    status     = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)

    # Filled in after simulation
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.home_club} vs {self.away_club} ({self.status})"


class MatchEvent(models.Model):
    """
    A single event in a match — goal, yellow card, substitution, etc.
    Stored as a chronological log; Phase 2 resolves them all at once
    (no live streaming yet — that's Phase 3 with Channels/WebSocket).
    """

    class EventType(models.TextChoices):
        GOAL       = "goal",       "Goal"
        YELLOW     = "yellow",     "Yellow card"
        RED        = "red",        "Red card"
        SUBSTITUTE = "substitute", "Substitution"
        MISS       = "miss",       "Missed chance"
        SAVE       = "save",       "Goalkeeper save"

    fixture    = models.ForeignKey(Fixture, on_delete=models.CASCADE, related_name="events")
    minute     = models.PositiveSmallIntegerField()
    event_type = models.CharField(max_length=12, choices=EventType.choices)
    club       = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="match_events")
    description = models.CharField(max_length=200)

    class Meta:
        ordering = ["minute"]

    def __str__(self):
        return f"{self.minute}' {self.event_type} – {self.club}"


class LeagueStanding(models.Model):
    """Denormalised table recomputed after each fixture by update_standings."""

    season  = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="standings")
    club    = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="standings")
    played  = models.PositiveSmallIntegerField(default=0)
    won     = models.PositiveSmallIntegerField(default=0)
    drawn   = models.PositiveSmallIntegerField(default=0)
    lost    = models.PositiveSmallIntegerField(default=0)
    gf      = models.PositiveSmallIntegerField(default=0)   # goals for
    ga      = models.PositiveSmallIntegerField(default=0)   # goals against
    points  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("season", "club")
        ordering = ["-points", "-gf"]

    @property
    def gd(self):
        return self.gf - self.ga

    def __str__(self):
        return f"{self.club} – {self.points} pts"
