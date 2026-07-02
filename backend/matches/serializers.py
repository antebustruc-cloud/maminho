from rest_framework import serializers

from .models import Fixture, LeagueStanding, MatchEvent


class MatchEventSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)

    class Meta:
        model  = MatchEvent
        fields = ["id", "minute", "event_type", "club_name", "description"]


class FixtureSerializer(serializers.ModelSerializer):
    home_club_name = serializers.CharField(source="home_club.name", read_only=True)
    away_club_name = serializers.CharField(source="away_club.name", read_only=True)
    events         = MatchEventSerializer(many=True, read_only=True)

    class Meta:
        model  = Fixture
        fields = [
            "id", "season", "home_club_name", "away_club_name",
            "scheduled_at", "status", "home_score", "away_score", "events",
        ]


class LeagueStandingSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True)
    gd        = serializers.SerializerMethodField()

    def get_gd(self, obj):
        return obj.gf - obj.ga

    class Meta:
        model  = LeagueStanding
        fields = ["club_name", "played", "won", "drawn", "lost", "gf", "ga", "gd", "points"]
