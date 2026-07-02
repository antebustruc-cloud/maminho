from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from clubs.models import Season

from .models import Fixture, LeagueStanding
from .serializers import FixtureSerializer, LeagueStandingSerializer
from .simulation import simulate_fixture


class FixtureListView(generics.ListAPIView):
    """List all fixtures, optionally filtered by season."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = FixtureSerializer

    def get_queryset(self):
        qs = Fixture.objects.select_related("home_club", "away_club", "season")
        season_id = self.request.query_params.get("season")
        if season_id:
            qs = qs.filter(season_id=season_id)
        return qs.order_by("scheduled_at")


class FixtureDetailView(generics.RetrieveAPIView):
    """Full fixture detail including event log."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = FixtureSerializer
    queryset           = Fixture.objects.prefetch_related("events")


class SimulateFixtureView(APIView):
    """
    POST /api/matches/<id>/simulate/
    Admin only. Runs the match engine and saves the result.
    In Phase 3 this becomes an async task triggered by a scheduler;
    for Phase 2 the admin triggers it manually or via cron.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, fixture_id):
        fixture = Fixture.objects.filter(id=fixture_id).first()
        if not fixture:
            raise ValidationError("Fixture not found.")
        if fixture.status == Fixture.Status.FINISHED:
            raise ValidationError("Fixture already finished.")

        fixture = simulate_fixture(fixture)
        return Response(FixtureSerializer(fixture).data)


class LeagueTableView(APIView):
    """GET /api/matches/standings/?season=<id>"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        season_id = request.query_params.get("season")
        if not season_id:
            active = Season.objects.filter(status=Season.Status.ACTIVE).order_by("-start_date").first()
            if not active:
                return Response([])
            season_id = active.id

        standings = (
            LeagueStanding.objects
            .filter(season_id=season_id)
            .select_related("club")
            .order_by("-points", "-gf", "ga")
        )
        return Response(LeagueStandingSerializer(standings, many=True).data)
