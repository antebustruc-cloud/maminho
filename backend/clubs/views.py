from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from economy.models import InsufficientFundsError, Transaction, move_kc

from . import facility_config
from .models import Club, ConstructionProject, Facility, Season, SeasonRegistration, SportLicense
from .serializers import (
    ClubSerializer,
    ConstructionProjectSerializer,
    SeasonRegistrationSerializer,
    SeasonSerializer,
)
from .services import register_for_season, start_construction


class IsClubOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.CLUB_OWNER


class MyClubView(generics.RetrieveAPIView):
    permission_classes = [IsClubOwner]
    serializer_class   = ClubSerializer

    def get_object(self):
        return self.request.user.club


class StartConstructionView(APIView):
    """
    POST {facility_type} — start a construction project (Phase 3b).
    No facility of that type yet → builds it (project L0→L1).
    Facility exists → upgrade project to the next level (max 7).
    KC is deducted at start; completion is applied by the
    complete_construction cron. Owner-only.
    """
    permission_classes = [IsClubOwner]

    def post(self, request):
        project = start_construction(request.user.club, request.data.get("facility_type"))
        return Response(ConstructionProjectSerializer(project).data,
                        status=status.HTTP_201_CREATED)


class BuildFacilityView(StartConstructionView):
    """Legacy endpoint — now starts a construction project (kept so existing
    frontend keeps working)."""


class UpgradeFacilityView(APIView):
    """Legacy endpoint — now starts an upgrade construction project."""
    permission_classes = [IsClubOwner]

    def post(self, request, facility_id):
        facility = Facility.objects.filter(id=facility_id, club=request.user.club).first()
        if not facility:
            raise PermissionDenied("Not your facility.")
        project = start_construction(request.user.club, facility.facility_type)
        return Response(ConstructionProjectSerializer(project).data,
                        status=status.HTTP_201_CREATED)


class FacilityLevelConfigView(APIView):
    """Read-only listing of the per-type, per-level construction config."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "max_level": facility_config.MAX_LEVEL,
            "levels": facility_config.LEVEL_CONFIG,
        })


class MyConstructionProjectsView(generics.ListAPIView):
    """Status of the owner's club construction projects (active first)."""
    permission_classes = [IsClubOwner]
    serializer_class   = ConstructionProjectSerializer

    def get_queryset(self):
        return (ConstructionProject.objects
                .filter(facility__club=self.request.user.club)
                .select_related("facility")
                .order_by("status", "-created_at"))


class RegisterForSeasonView(APIView):
    """POST — register the owner's club for a season (owner-only for now)."""
    permission_classes = [IsClubOwner]

    def post(self, request, season_id):
        season = Season.objects.filter(id=season_id).first()
        if not season:
            raise ValidationError("Unknown season.")
        registration = register_for_season(request.user.club, season)
        return Response(SeasonRegistrationSerializer(registration).data,
                        status=status.HTTP_201_CREATED)


class SeasonRegistrationsView(generics.ListAPIView):
    """Public list of clubs registered for a season."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = SeasonRegistrationSerializer

    def get_queryset(self):
        return (SeasonRegistration.objects
                .filter(season_id=self.kwargs["season_id"])
                .select_related("club")
                .order_by("registered_at"))


class PurchaseSportLicenseView(APIView):
    permission_classes = [IsClubOwner]

    def post(self, request):
        club = request.user.club
        sport = request.data.get("sport")
        if sport not in SportLicense.Sport.values:
            raise ValidationError("Unknown sport.")
        if club.sport_licenses.filter(sport=sport).exists():
            raise ValidationError("Club already holds this license.")

        required = SportLicense.REQUIRED_FACILITY[sport]
        if not club.facilities.filter(facility_type=required).exists():
            raise ValidationError(f"Requires a {required} facility first.")

        cost = SportLicense.LICENSE_COSTS[sport]
        try:
            move_kc(from_holder=club, to_holder=None, amount=cost,
                     kind=Transaction.Kind.SPORT_LICENSE,
                     description=f"Purchased {sport} license")
        except InsufficientFundsError as exc:
            raise ValidationError(str(exc))

        lic = SportLicense.objects.create(club=club, sport=sport)
        return Response({"id": lic.id, "sport": sport}, status=status.HTTP_201_CREATED)


class CurrentSeasonView(APIView):
    """Public — anyone can check what season is running."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sport  = request.query_params.get("sport", "football")
        season = Season.objects.filter(sport=sport, status=Season.Status.ACTIVE).first()
        if not season:
            offseason = Season.objects.filter(sport=sport, status=Season.Status.UPCOMING).order_by("start_date").first()
            if offseason:
                return Response({"status": "offseason", "next_season": SeasonSerializer(offseason).data})
            return Response({"status": "offseason", "next_season": None})
        return Response({"status": "active", "season": SeasonSerializer(season).data})
